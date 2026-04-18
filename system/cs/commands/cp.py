from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import json
from copy import deepcopy

from system.cs.command_args import parse_argv
from system.cs.lib.ops import child_suffix, copy_subtree
from system.lib.map.structure import materialize_under_hash
from system.lib.symbols import (
    SymbolError,
    clear_symbol_tree,
    resolve_raw_exact,
    state_side_only,
    stringify_resolved,
    symbol_exists_or_has_children,
    symbol_root,
    try_parse_structured_json,
    validate_symbol,
    write_symbol_value,
)


command = "cp"
help_short = 'cp <src> <dst>'
help_full = """copy one state-side symbol or subtree

rules:
- cp applies only to state-side symbols
- runtime spaces ! @ % | are not valid cp targets or sources
- same-root subtree copy preserves structure
- # -> $ dumps structured content as one string payload
- $ -> # materializes parsed structured content when possible
- cross-root scalar copy writes one scalar value
"""

def _ensure_not_same(source: str, target: str, verb: str) -> None:
    if source == target:
        raise ValueError(f"{verb} source and target cannot be the same")


def _ensure_no_overlap(source: str, target: str, verb: str) -> None:
    if source == target:
        raise ValueError(f"{verb} source and target cannot be the same")
    if child_suffix(target, source) not in (None, ""):
        raise ValueError(f"{verb} target cannot be inside source")
    if child_suffix(source, target) not in (None, ""):
        raise ValueError(f"{verb} source and target cannot overlap")


def _ensure_target_empty(state, target: str, verb: str) -> None:
    if symbol_exists_or_has_children(state, target):
        raise ValueError(f"{verb} target already exists")


def _copy_same_root(state, source: str, target: str, *, writer: str) -> None:
    _ensure_no_overlap(source, target, "cp")
    _ensure_target_empty(state, target, "cp")
    copy_subtree(state, source, target, writer=writer, op="cp_copy_subtree")


def _copy_hash_to_dollar(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "cp")
    _ensure_target_empty(state, target, "cp")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    payload = stringify_resolved(value)
    write_symbol_value(state, target, payload, writer=writer, op="cp_hash_to_dollar")


def _copy_value_to_hash(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "cp")
    _ensure_target_empty(state, target, "cp")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    structured = try_parse_structured_json(value)
    if structured is not None:
        materialize_under_hash(state, target, structured, writer=writer, op_prefix="cp_value_to_hash")
        return
    if isinstance(value, (dict, list)):
        materialize_under_hash(state, target, value, writer=writer, op_prefix="cp_value_to_hash")
        return
    write_symbol_value(state, target, deepcopy(value), writer=writer, op="cp_scalar_to_hash")


def _copy_cross_root_scalar(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "cp")
    _ensure_target_empty(state, target, "cp")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    if isinstance(value, (dict, list)):
        raise ValueError("cp cross-root copy requires scalar source")
    write_symbol_value(state, target, deepcopy(value), writer=writer, op="cp_cross_root_write")


def handler(line: str, parser):
    try:
        _, source, target = parse_argv(line, usage="usage: cp <source> <target>", label="cp", exact=2)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        src_root = validate_symbol(source)
        dst_root = validate_symbol(target)
        state_side_only(source, "cp")
        state_side_only(target, "cp")
        writer = "parser:cp"

        if src_root == dst_root:
            _copy_same_root(parser.state, source, target, writer=writer)
        elif src_root == "#" and dst_root == "$":
            _copy_hash_to_dollar(parser.state, source, target, writer=writer)
        elif src_root == "$" and dst_root == "#":
            _copy_value_to_hash(parser.state, source, target, writer=writer)
        else:
            _copy_cross_root_scalar(parser.state, source, target, writer=writer)
    except (ValueError, SymbolError) as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str("[ok]" or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

