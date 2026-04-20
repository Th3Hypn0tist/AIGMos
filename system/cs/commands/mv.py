from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv
from system.cs.lib.ops import child_suffix, move_subtree
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


command = "mv"
help_short = 'mv <src> <dst>'
help_full = """move one state-side symbol or subtree

rules:
- mv applies only to state-side symbols
- runtime spaces ! @ % | are not valid mv targets or sources
- move is copy then remove
- # <-> $ structural conversion rules mirror cp
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


def _move_same_root(state, source: str, target: str, *, writer: str) -> None:
    _ensure_no_overlap(source, target, "mv")
    _ensure_target_empty(state, target, "mv")
    move_subtree(state, source, target, writer=writer, write_op="mv_move_subtree_write", delete_op="mv_move_subtree_delete")


def _delete_source_tree(state, source: str, *, writer: str, op: str) -> None:
    clear_symbol_tree(state, source, writer=writer, op=op)


def _move_hash_to_dollar(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "mv")
    _ensure_target_empty(state, target, "mv")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    write_symbol_value(state, target, stringify_resolved(value), writer=writer, op="mv_hash_to_dollar")
    _delete_source_tree(state, source, writer=writer, op="mv_hash_to_dollar_delete")


def _move_value_to_hash(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "mv")
    _ensure_target_empty(state, target, "mv")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    structured = try_parse_structured_json(value)
    if structured is not None:
        materialize_under_hash(state, target, structured, writer=writer, op_prefix="mv_value_to_hash")
    elif isinstance(value, (dict, list)):
        materialize_under_hash(state, target, value, writer=writer, op_prefix="mv_value_to_hash")
    else:
        write_symbol_value(state, target, value, writer=writer, op="mv_scalar_to_hash")
    _delete_source_tree(state, source, writer=writer, op="mv_value_to_hash_delete")


def _move_cross_root_scalar(state, source: str, target: str, *, writer: str) -> None:
    _ensure_not_same(source, target, "mv")
    _ensure_target_empty(state, target, "mv")
    value = resolve_raw_exact(state, source)
    if value is None:
        raise ValueError("source not found")
    if isinstance(value, (dict, list)):
        raise ValueError("mv cross-root move requires scalar source")
    write_symbol_value(state, target, value, writer=writer, op="mv_cross_root_write")
    _delete_source_tree(state, source, writer=writer, op="mv_cross_root_delete")


def handler(line: str, parser):
    try:
        _, source, target = parse_argv(line, usage="usage: mv <source> <target>", label="mv", exact=2)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        src_root = validate_symbol(source)
        dst_root = validate_symbol(target)
        state_side_only(source, "mv")
        state_side_only(target, "mv")
        writer = "parser:mv"

        if src_root == dst_root:
            _move_same_root(parser.state, source, target, writer=writer)
        elif src_root == "#" and dst_root == "$":
            _move_hash_to_dollar(parser.state, source, target, writer=writer)
        elif src_root == "$" and dst_root == "#":
            _move_value_to_hash(parser.state, source, target, writer=writer)
        else:
            _move_cross_root_scalar(parser.state, source, target, writer=writer)
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

