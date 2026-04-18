from __future__ import annotations
from typing import Any
from system.extensions import guarded_symbol_read_allowed, guarded_symbol_write_allowed
def read_value(state, symbol: str, default: Any = None) -> Any:
    if not guarded_symbol_read_allowed(state, symbol):
        return default
    out = state.read_state(symbol) if hasattr(state, "read_state") else state.get(symbol)
    if out.get("error"):
        return default
    value = out.get("result")
    return default if value is None else value
def write_value(state, symbol: str, value: Any, *, writer: str = "system", op: str = "set") -> dict[str, Any]:
    if not guarded_symbol_write_allowed(state, symbol):
        return {"error": f"forbidden symbol write: {symbol}", "result": None}
    if hasattr(state, "write_state"):
        return state.write_state(symbol, value, writer=writer, op=op)
    return state.set(symbol, value)
def delete_value(state, symbol: str, *, writer: str = "system", op: str = "delete") -> dict[str, Any]:
    if not guarded_symbol_write_allowed(state, symbol):
        return {"error": f"forbidden symbol write: {symbol}", "result": None}
    if hasattr(state, "delete_state"):
        return state.delete_state(symbol, writer=writer, op=op)
    return state.delete(symbol)
def append_numeric_value(state, symbol: str, value: Any, *, writer: str = "system", op: str = "append") -> dict[str, Any]:
    if not guarded_symbol_write_allowed(state, symbol):
        return {"error": f"forbidden symbol write: {symbol}", "result": None}
    if hasattr(state, "append_numeric"):
        return state.append_numeric(symbol, value, writer=writer, op=op)
    current = read_value(state, symbol, None)
    text = "" if value is None else str(value)
    if current is None:
        payload = {"0": text}
    elif isinstance(current, dict):
        payload = dict(current)
        next_index = -1
        for key in payload.keys():
            try:
                next_index = max(next_index, int(str(key)))
            except Exception:
                continue
        payload[str(next_index + 1)] = text
    elif isinstance(current, list):
        payload = list(current)
        payload.append(text)
    elif isinstance(current, str):
        payload = current + ("\n" if current and text else "") + text
    else:
        payload = {"0": text}
    return write_value(state, symbol, payload, writer=writer, op=op)
def list_symbols(state) -> list[str]:
    out = state.list_symbols()
    if out.get("error"):
        raise ValueError(out["error"])
    items = sorted(str(item) for item in out.get("result") or [])
    return [item for item in items if guarded_symbol_read_allowed(state, item)]
