from __future__ import annotations

from typing import Any, Dict

from system.state.api import read_value, write_value


RUNNER_DEFS_SYMBOL = "#SYSTEM:runtime:runners"


def _runner_writer(name: str) -> str:
    clean = str(name or "").strip()
    return f"runner_store:{clean}" if clean else "runner_store:unknown"


class RunnerDefError(ValueError):
    pass


def _state_get_value(state, symbol: str):
    return read_value(state, symbol, None)


def _state_set_value(state, symbol: str, value: Any, *, writer: str = "runner_store:persist") -> None:
    out = write_value(state, symbol, value, writer=writer, op="runner_persist")
    if out["error"]:
        raise RunnerDefError(out["error"])


def _normalize_autostart(value: Any) -> int:
    if value in (None, "", False):
        return 0
    if isinstance(value, bool):
        raise RunnerDefError("autostart must be integer >= 0")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise RunnerDefError("autostart must be integer >= 0")
    if number < 0:
        raise RunnerDefError("autostart must be integer >= 0")
    return number


def _normalize_def(name: str, item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        raise RunnerDefError(f"invalid runner definition: {name}")

    source = str(item.get("source") or "")
    mode = str(item.get("mode") or "")
    lines = item.get("lines") or []
    autostart = _normalize_autostart(item.get("autostart", 0))

    if not name.startswith("%"):
        raise RunnerDefError(f"invalid runner name: {name}")
    if not source:
        raise RunnerDefError(f"missing runner source: {name}")
    if not isinstance(lines, list):
        raise RunnerDefError(f"runner lines must be list: {name}")

    return {
        "name": name,
        "source": source,
        "mode": mode,
        "lines": [str(x) for x in lines],
        "autostart": autostart,
    }


def load_runner_defs(state) -> Dict[str, Dict[str, Any]]:
    data = _state_get_value(state, RUNNER_DEFS_SYMBOL)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RunnerDefError("#SYSTEM:runtime:runners must be dict")

    out: Dict[str, Dict[str, Any]] = {}
    for name, item in data.items():
        normalized = _normalize_def(str(name), item)
        out[normalized["name"]] = normalized
    return out


def save_runner_defs(state, defs: Dict[str, Dict[str, Any]], *, writer: str = "runner_store:persist") -> None:
    payload: Dict[str, Dict[str, Any]] = {}
    for name, item in defs.items():
        normalized = _normalize_def(name, item)
        payload[normalized["name"]] = {
            "source": normalized["source"],
            "mode": normalized["mode"],
            "lines": normalized["lines"],
            "autostart": normalized["autostart"],
        }
    _state_set_value(state, RUNNER_DEFS_SYMBOL, payload, writer=writer)


def upsert_runner_def(
    state,
    *,
    name: str,
    source: str,
    mode: str,
    lines: list[str],
    autostart: Any = 0,
) -> Dict[str, Any]:
    defs = load_runner_defs(state)
    normalized = _normalize_def(
        name,
        {
            "source": source,
            "mode": mode,
            "lines": lines,
            "autostart": autostart,
        },
    )
    defs[name] = normalized
    save_runner_defs(state, defs, writer=_runner_writer(name))
    return normalized


def delete_runner_def(state, name: str) -> bool:
    defs = load_runner_defs(state)
    if name not in defs:
        return False
    defs.pop(name, None)
    save_runner_defs(state, defs, writer=_runner_writer(name))
    return True


def set_runner_autostart(state, name: str, value: Any) -> int:
    defs = load_runner_defs(state)
    item = defs.get(name)
    if item is None:
        raise RunnerDefError(f"runner not found: {name}")
    item["autostart"] = _normalize_autostart(value)
    defs[name] = _normalize_def(name, item)
    save_runner_defs(state, defs, writer=_runner_writer(name))
    return defs[name]["autostart"]


def set_runner_mode_persistent(state, name: str, mode: str) -> None:
    defs = load_runner_defs(state)
    item = defs.get(name)
    if item is None:
        raise RunnerDefError(f"runner not found: {name}")
    item["mode"] = str(mode)
    defs[name] = _normalize_def(name, item)
    save_runner_defs(state, defs, writer=_runner_writer(name))
