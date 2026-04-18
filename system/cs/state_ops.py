from __future__ import annotations

from typing import Any

from system.state.api import delete_value, read_value, write_value


def get_result(state, symbol: str) -> Any:
    return read_value(state, symbol, None)


def get_optional(state, symbol: str) -> Any:
    return get_result(state, symbol)


def get_required(state, symbol: str, *, message: str | None = None) -> Any:
    value = get_result(state, symbol)
    if value is None:
        raise ValueError(message or f"symbol not found: {symbol}")
    return value


def set_result(
    state,
    symbol: str,
    value: Any,
    *,
    writer: str = "parser:unknown",
    op: str = "set_result",
) -> Any:
    out = write_value(state, symbol, value, writer=writer, op=op)
    if out.get("error"):
        raise ValueError(str(out["error"]))
    return out.get("result")


def delete_result(
    state,
    symbol: str,
    *,
    writer: str = "parser:unknown",
    op: str = "delete_result",
) -> None:
    out = delete_value(state, symbol, writer=writer, op=op)
    if out.get("error"):
        raise ValueError(str(out["error"]))


def exists(state, symbol: str) -> bool:
    return get_result(state, symbol) is not None
