from __future__ import annotations

from typing import Any

from system.lib.symbols import (
    clear_symbol_tree,
    list_symbols,
    read_symbol_value,
    validate_symbol,
    write_symbol_value,
)


def build_directory_rows(state, src: str) -> list[str]:
    validate_symbol(src, allowed="#", role="input")

    exact = read_symbol_value(state, src, None)
    symbols = list_symbols(state)
    has_exact = exact is not None
    has_children = any(symbol.startswith(src + ":") for symbol in symbols)
    if not has_exact and not has_children:
        raise ValueError("target not found")

    rows = set()
    prefix = src + ":"
    for symbol in symbols:
        if symbol == src or not symbol.startswith(prefix):
            continue
        rel = symbol[len(prefix):].strip()
        if not rel:
            continue
        parts = [part.strip() for part in rel.split(":") if part.strip()]
        if len(parts) < 2:
            continue
        for i in range(len(parts) - 1):
            rows.add("/".join(parts[: i + 1]) + "/")

    return sorted(rows, key=lambda item: [segment.lower() for segment in item.rstrip("/").split("/")])


def materialize_under_hash(state, target: str, value: Any, *, writer: str, op_prefix: str = "materialize") -> None:
    validate_symbol(target, allowed="#", role="target")
    clear_symbol_tree(state, target, writer=writer, op=f"{op_prefix}_clear")
    _materialize_node(state, target, value, writer=writer, op_prefix=op_prefix)


def _materialize_node(state, target: str, value: Any, *, writer: str, op_prefix: str) -> None:
    if isinstance(value, dict):
        if not value:
            write_symbol_value(state, target, {}, writer=writer, op=f"{op_prefix}_empty_dict")
            return
        for key, item in value.items():
            child = f"{target}:{key}"
            _materialize_node(state, child, item, writer=writer, op_prefix=op_prefix)
        return

    if isinstance(value, list):
        if not value:
            write_symbol_value(state, target, [], writer=writer, op=f"{op_prefix}_empty_list")
            return
        for idx, item in enumerate(value):
            child = f"{target}:{idx}"
            _materialize_node(state, child, item, writer=writer, op_prefix=op_prefix)
        return

    write_symbol_value(state, target, value, writer=writer, op=f"{op_prefix}_leaf")
