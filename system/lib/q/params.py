"""Q runtime parameter helpers.

Owns only Q-specific runtime override reading and primitive coercion.
"""

from __future__ import annotations

from .symbols import q_state_prefix_for_state
from .common import normalize_think_value


def _unwrap_state_result(value):
    if isinstance(value, dict) and "result" in value and "error" in value:
        if value.get("error"):
            return None
        return value.get("result")
    return value


def _state_get(state, symbol: str):
    if state is None:
        return None

    for name in ("read_state", "get", "read", "read_value", "get_value", "get_symbol", "read_symbol"):
        fn = getattr(state, name, None)
        if not callable(fn):
            continue
        try:
            value = fn(symbol)
        except TypeError:
            try:
                value = fn(symbol, None)
            except Exception:
                continue
        except Exception:
            continue
        return _unwrap_state_result(value)

    return None


def _parser_get(parser, symbol: str):
    if parser is None:
        return None

    state = getattr(parser, "state", None)
    value = _state_get(state, symbol)
    if value is not None:
        return value

    for name in ("read_value", "get_value", "read_symbol", "get_symbol"):
        fn = getattr(parser, name, None)
        if not callable(fn):
            continue
        try:
            value = fn(symbol)
        except TypeError:
            try:
                value = fn(symbol, None)
            except Exception:
                continue
        except Exception:
            continue
        return _unwrap_state_result(value)

    return None


def _clean(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def coerce_bool(value):
    s = _clean(value)
    if s is None:
        return None
    s = s.lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return None


def coerce_int(value):
    s = _clean(value)
    if s is None:
        return None
    try:
        return int(s)
    except Exception:
        return None


def coerce_float(value):
    s = _clean(value)
    if s is None:
        return None
    try:
        return float(s)
    except Exception:
        return None


def coerce_str(value):
    return _clean(value)


def read_q_param(parser, profile_name: str, key: str):
    roots = []
    state = getattr(parser, "state", None)
    runtime_prefix = q_state_prefix_for_state(state, profile_name)
    if runtime_prefix:
        roots.append(f"{runtime_prefix}:{key}")
    if profile_name and profile_name != "default":
        roots.append(f"$Q.{profile_name}:{key}")
    roots.append(f"$Q:{key}")

    seen = set()
    for symbol in roots:
        if symbol in seen:
            continue
        seen.add(symbol)
        value = _parser_get(parser, symbol)
        value = _clean(value)
        if value is not None:
            return value

    return None


def collect_q_overrides(parser, profile_name: str) -> dict:
    spec = {
        "heat": coerce_float,
        "think": normalize_think_value,
        "thinking": normalize_think_value,
        "stream": coerce_bool,
        "top_p": coerce_float,
        "top_k": coerce_int,
        "repeat_penalty": coerce_float,
        "max_tokens": coerce_int,
        "timeout_seconds": coerce_int,
        "stream_timeout_seconds": coerce_int,
        "model": coerce_str,
        "seed": coerce_int,
        "num_ctx": coerce_int,
    }

    out = {}
    for key, caster in spec.items():
        raw = read_q_param(parser, profile_name, key)
        value = caster(raw)
        if value is not None:
            out[key] = value
    return out
