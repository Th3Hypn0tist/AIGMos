from __future__ import annotations

from typing import Any

from system.state.api import list_symbols as list_state_symbols, write_value

from .common import read_state_value, q_writer
from .errors import QCallError
from .profile import read_q_override, resolve_think_value, read_state_override
from .symbols import q_sampler_prefix_for_profile


_Q_SAMPLER_DEFAULTS = {
    "temperature": 0.6,
    "top_k": 20,
    "top_p": 0.95,
    "repeat_penalty": 1.0,
}

def _write_sampler_symbol_if_missing(state, symbol: str, value: Any, *, op: str, profile_name: str = "default") -> None:
    current = read_state_value(state, symbol, None)
    if current is not None:
        return
    out = write_value(state, symbol, value, writer=q_writer(profile_name), op=op)
    if out["error"]:
        raise QCallError(out["error"])


def ensure_q_sampler_state(state, profile_name: str = "default") -> None:
    prefix = q_sampler_prefix_for_profile(profile_name)
    for key, value in _Q_SAMPLER_DEFAULTS.items():
        _write_sampler_symbol_if_missing(state, f"{prefix}:{key}", value, op=f"sampler_seed_{key}", profile_name=profile_name)


def _coerce_sampler_number(raw: Any, *, key: str, as_int: bool):
    if raw in (None, ""):
        return None
    try:
        number = int(raw) if as_int else float(raw)
    except Exception as exc:
        raise QCallError(f"invalid sampler value for {key}: {raw}") from exc
    if key == "top_k" and number < 0:
        raise QCallError("invalid sampler value for top_k: must be >= 0")
    if key in ("temperature", "top_p", "repeat_penalty") and float(number) < 0:
        raise QCallError(f"invalid sampler value for {key}: must be >= 0")
    return number



def resolve_q_sampler_values(profile: dict, state, profile_name: str) -> dict[str, Any]:
    ensure_q_sampler_state(state, profile_name)
    values: dict[str, Any] = {}

    q_overrides = {
        "temperature": read_q_override(state, profile_name, "temperature"),
        "heat": read_q_override(state, profile_name, "heat"),
        "top_k": read_q_override(state, profile_name, "top_k"),
        "top_p": read_q_override(state, profile_name, "top_p"),
        "repeat_penalty": read_q_override(state, profile_name, "repeat_penalty"),
        "max_tokens": read_q_override(state, profile_name, "max_tokens"),
        "seed": read_q_override(state, profile_name, "seed"),
        "num_ctx": read_q_override(state, profile_name, "num_ctx"),
    }

    numeric_fields = (("temperature", False), ("top_k", True), ("top_p", False), ("repeat_penalty", False))
    for key, as_int in numeric_fields:
        raw = q_overrides.get(key)
        if key == "temperature" and raw in (None, ""):
            raw = q_overrides.get("heat")
        if raw in (None, ""):
            raw = read_state_override(state, f"{q_sampler_prefix_for_profile(profile_name)}:{key}")
        if raw in (None, "") and profile_name != "default":
            raw = read_state_override(state, f"$q:{key}")
        if raw in (None, ""):
            raw = profile.get(key)
        if raw in (None, "") and key == "temperature":
            raw = profile.get("heat")
        if raw in (None, ""):
            raw = _Q_SAMPLER_DEFAULTS[key]
        coerced = _coerce_sampler_number(raw, key=key, as_int=as_int)
        if coerced is not None:
            values[key] = coerced


    for extra_key in ("max_tokens", "seed", "num_ctx"):
        extra_value = q_overrides.get(extra_key)
        if extra_value in (None, ""):
            extra_value = profile.get(extra_key)
        if extra_value not in (None, ""):
            values[extra_key] = extra_value

    think_value = resolve_think_value(profile, state, profile_name)
    if think_value is not None:
        values["think"] = think_value

    return values


def get_q_sampler_state(state, profile_name: str = "default") -> dict[str, Any]:
    return resolve_q_sampler_values({}, state, profile_name)


__all__ = [
    "ensure_q_sampler_state",
    "get_q_sampler_state",
    "q_sampler_prefix_for_profile",
    "resolve_q_sampler_values",
]
