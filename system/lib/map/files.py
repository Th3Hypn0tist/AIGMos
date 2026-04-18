from __future__ import annotations

from system.lib.symbols import list_symbols, read_symbol_value, validate_symbol


def build_file_rows(state, src: str) -> list[str]:
    validate_symbol(src, allowed="#", role="input")

    direct = read_symbol_value(state, src, None)
    symbols = list_symbols(state)
    has_exact = direct is not None
    has_children = any(symbol.startswith(src + ":") for symbol in symbols)
    if not has_exact and not has_children:
        raise ValueError("target not found")

    rows = set()
    if has_exact and not has_children:
        rows.add(_basename(src))

    prefix = src + ":"
    for symbol in symbols:
        if symbol == src or not symbol.startswith(prefix):
            continue
        rel = symbol[len(prefix):].strip()
        if not rel:
            continue
        parts = [part.strip() for part in rel.split(":") if part.strip()]
        if not parts:
            continue
        for i in range(len(parts) - 1):
            rows.add("/".join(parts[: i + 1]) + "/")
        value = read_symbol_value(state, symbol, None)
        if isinstance(value, dict):
            rows.add("/".join(parts) + "/")
        else:
            rows.add("/".join(parts))

    return sorted(rows, key=lambda item: [segment.lower() for segment in item.rstrip("/").split("/")])


def _basename(symbol: str) -> str:
    if ":" in symbol:
        return symbol.rsplit(":", 1)[1]
    return symbol[1:]
