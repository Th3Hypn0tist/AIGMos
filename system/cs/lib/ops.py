from __future__ import annotations

from copy import deepcopy
from typing import Any, List, Tuple

from system.state.api import delete_value, list_symbols as _api_list_symbols, read_value, write_value
from system.extensions import assert_extension_symbol_read_allowed, assert_extension_symbol_write_allowed
from system.lib.symbols import ALL_ROOTS, RUNTIME_ROOTS, STATE_ROOTS, symbol_root as _symbol_root, validate_symbol as _validate_symbol, state_side_only as _state_side_only



def _assert_read_allowed(state, symbol: str) -> None:
    try:
        assert_extension_symbol_read_allowed(state, symbol)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def _assert_write_allowed(state, symbol: str) -> None:
    try:
        assert_extension_symbol_write_allowed(state, symbol)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

PRIMITIVE_HELP = {
    "$": "structured state",
    "#": "structured address / namespace",
    "&": "list",
    "%": "runners runtime",
    "!": "triggers runtime",
    "@": "events runtime",
    "|": "layout runtime",
}


def symbol_root(symbol: str) -> str:
    return _symbol_root(symbol)


def validate_symbol(symbol: str, *, allow_bare_root: bool = False) -> str:
    try:
        return _validate_symbol(symbol, allow_bare_root=allow_bare_root, role="target")
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def is_runtime_symbol(symbol: str) -> bool:
    return symbol_root(symbol) in RUNTIME_ROOTS


def state_side_only(symbol: str, verb: str) -> None:
    try:
        _state_side_only(symbol, verb)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def separator_variants(symbol: str) -> tuple[str, ...]:
    root = symbol_root(symbol)
    if root == "#":
        return (":",)
    if root == "$":
        return (":", ".")
    if root == "&":
        return (":", ".")
    return (":", ".")


def child_suffix(symbol: str, prefix: str) -> str | None:
    if symbol == prefix:
        return ""
    for sep in separator_variants(prefix):
        head = prefix + sep
        if symbol.startswith(head):
            return symbol[len(prefix):]
    return None


def direct_child_name(symbol: str, prefix: str) -> str | None:
    suffix = child_suffix(symbol, prefix)
    if suffix in (None, ""):
        return None
    rest = suffix[1:]
    if not rest:
        return None
    for sep in separator_variants(prefix):
        if sep in rest:
            return rest.split(sep, 1)[0]
    return rest


def list_symbols(state) -> List[str]:
    return _api_list_symbols(state)


def wildcard_prefix_match(state, pattern: str) -> List[str]:
    if not pattern.endswith("*"):
        raise ValueError("wildcard pattern must end with *")
    if pattern.count("*") != 1:
        raise ValueError("only one wildcard is allowed")
    if pattern.startswith("*") or "*" in pattern[:-1]:
        raise ValueError("* is allowed only at the end")
    prefix = pattern[:-1]
    validate_symbol(prefix, allow_bare_root=True)
    _assert_read_allowed(state, prefix)
    return [symbol for symbol in list_symbols(state) if symbol.startswith(prefix)]


def _exact_symbol_exists(symbols: List[str], source: str) -> bool:
    return source in symbols


def _require_writer(writer: str | None) -> str:
    clean = str(writer or "").strip()
    if not clean or clean == "alias":
        raise ValueError("writer tag required")
    return clean


def get_subtree(state, source: str) -> List[Tuple[str, Any]]:
    state_side_only(source, "operation")
    _assert_read_allowed(state, source)
    symbols = list_symbols(state)
    subtree_symbols: List[str] = []
    for symbol in symbols:
        if child_suffix(symbol, source) is not None:
            subtree_symbols.append(symbol)

    if not subtree_symbols:
        value = read_value(state, source, None)
        if value is None and not _exact_symbol_exists(symbols, source):
            raise ValueError("source not found")
        return [(source, deepcopy(value))]

    items = []
    for symbol in subtree_symbols:
        items.append((symbol, deepcopy(read_value(state, symbol, None))))
    return items


def copy_subtree(
    state,
    source: str,
    target: str,
    *,
    writer: str,
    op: str = "copy_subtree",
) -> None:
    writer = _require_writer(writer)
    state_side_only(source, "cp")
    state_side_only(target, "cp")
    _assert_read_allowed(state, source)
    _assert_write_allowed(state, target)
    _ensure_same_root(source, target, "cp")
    _ensure_not_same(source, target, "cp")

    items = get_subtree(state, source)
    for symbol, value in items:
        new_symbol = target + symbol[len(source):]
        out = write_value(state, new_symbol, value, writer=writer, op=op)
        if out.get("error"):
            raise ValueError(out["error"])


def move_subtree(
    state,
    source: str,
    target: str,
    *,
    writer: str,
    write_op: str = "move_subtree_write",
    delete_op: str = "move_subtree_delete",
) -> None:
    writer = _require_writer(writer)
    state_side_only(source, "mv")
    state_side_only(target, "mv")
    _assert_read_allowed(state, source)
    _assert_write_allowed(state, target)
    _ensure_same_root(source, target, "mv")
    _ensure_not_same(source, target, "mv")

    items = get_subtree(state, source)
    for symbol, value in items:
        new_symbol = target + symbol[len(source):]
        out = write_value(state, new_symbol, value, writer=writer, op=write_op)
        if out.get("error"):
            raise ValueError(out["error"])

    for symbol, _ in sorted(items, key=lambda item: len(item[0]), reverse=True):
        out = delete_value(state, symbol, writer=writer, op=delete_op)
        if out.get("error"):
            raise ValueError(out["error"])


def remove_subtree(
    state,
    target: str,
    *,
    writer: str,
    op: str = "remove_subtree",
) -> None:
    writer = _require_writer(writer)
    validate_symbol(target)
    _assert_write_allowed(state, target)
    if is_runtime_symbol(target):
        return
    items = get_subtree(state, target)
    for symbol, _ in sorted(items, key=lambda item: len(item[0]), reverse=True):
        out = delete_value(state, symbol, writer=writer, op=op)
        if out.get("error"):
            raise ValueError(out["error"])


def _ensure_same_root(source: str, target: str, verb: str) -> None:
    if symbol_root(source) != symbol_root(target):
        raise ValueError(f"{verb} requires the same root primitive")


def _ensure_not_same(source: str, target: str, verb: str) -> None:
    if target == source:
        raise ValueError(f"{verb} source and target cannot be the same")
