# system/cs/lib/ops.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, List, Tuple

RUNTIME_ROOTS = {"%", "!", "@"}
STATE_ROOTS = {"$", "#", "&"}
ALL_ROOTS = STATE_ROOTS | RUNTIME_ROOTS
PRIMITIVE_HELP = {
    "$": "structured state",
    "#": "structured address / namespace",
    "&": "list",
    "%": "runners runtime",
    "!": "triggers runtime",
    "@": "events runtime",
}


def symbol_root(symbol: str) -> str:
    return symbol[:1]


def validate_symbol(symbol: str, *, allow_bare_root: bool = False) -> str:
    if not symbol:
        raise ValueError("empty target")
    root = symbol_root(symbol)
    if root not in ALL_ROOTS:
        raise ValueError("target must start with $, #, &, %, ! or @")
    if not allow_bare_root and len(symbol) == 1:
        raise ValueError("target must not be a bare root")
    return root


def is_runtime_symbol(symbol: str) -> bool:
    return symbol_root(symbol) in RUNTIME_ROOTS


def state_side_only(symbol: str, verb: str) -> None:
    root = validate_symbol(symbol)
    if root in RUNTIME_ROOTS:
        raise ValueError(f"{verb} does not apply to runtime spaces")


def list_symbols(state) -> List[str]:
    out = state.list_symbols()
    if out["error"]:
        raise ValueError(out["error"])
    return sorted(str(item) for item in out["result"] or [])


def wildcard_prefix_match(state, pattern: str) -> List[str]:
    if not pattern.endswith("*"):
        raise ValueError("wildcard pattern must end with *")
    if pattern.count("*") != 1:
        raise ValueError("only one wildcard is allowed")
    if pattern.startswith("*") or "*" in pattern[:-1]:
        raise ValueError("* is allowed only at the end")
    prefix = pattern[:-1]
    validate_symbol(prefix, allow_bare_root=True)
    return [symbol for symbol in list_symbols(state) if symbol.startswith(prefix)]


def get_subtree(state, source: str) -> List[Tuple[str, Any]]:
    state_side_only(source, "operation")
    sep = _separator_for(source)
    symbols = [
        symbol
        for symbol in list_symbols(state)
        if symbol == source or symbol.startswith(source + sep)
    ]
    if not symbols:
        value = state.get(source)
        if value["error"]:
            raise ValueError(value["error"])
        if value["result"] is None:
            raise ValueError("source not found")
        return [(source, deepcopy(value["result"]))]

    items = []
    for symbol in symbols:
        out = state.get(symbol)
        if out["error"]:
            raise ValueError(out["error"])
        items.append((symbol, deepcopy(out["result"])))
    return items


def copy_subtree(state, source: str, target: str) -> None:
    state_side_only(source, "cp")
    state_side_only(target, "cp")
    _ensure_same_root(source, target, "cp")
    _ensure_not_same(source, target, "cp")

    items = get_subtree(state, source)
    for symbol, value in items:
        new_symbol = target + symbol[len(source):]
        out = state.set(new_symbol, value)
        if out["error"]:
            raise ValueError(out["error"])


def move_subtree(state, source: str, target: str) -> None:
    state_side_only(source, "mv")
    state_side_only(target, "mv")
    _ensure_same_root(source, target, "mv")
    _ensure_not_same(source, target, "mv")

    items = get_subtree(state, source)
    for symbol, value in items:
        new_symbol = target + symbol[len(source):]
        out = state.set(new_symbol, value)
        if out["error"]:
            raise ValueError(out["error"])

    for symbol, _ in sorted(items, key=lambda item: len(item[0]), reverse=True):
        out = state.delete(symbol)
        if out["error"]:
            raise ValueError(out["error"])


def remove_subtree(state, target: str) -> None:
    validate_symbol(target)
    if is_runtime_symbol(target):
        return
    items = get_subtree(state, target)
    for symbol, _ in sorted(items, key=lambda item: len(item[0]), reverse=True):
        out = state.delete(symbol)
        if out["error"]:
            raise ValueError(out["error"])


def _ensure_same_root(source: str, target: str, verb: str) -> None:
    if symbol_root(source) != symbol_root(target):
        raise ValueError(f"{verb} requires the same root primitive")


def _ensure_not_same(source: str, target: str, verb: str) -> None:
    if target == source:
        raise ValueError(f"{verb} source and target cannot be the same")


def _separator_for(symbol: str) -> str:
    return ":" if symbol.startswith("#") else "."
