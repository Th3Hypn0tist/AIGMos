from __future__ import annotations

import json
from typing import Any

from system.state.api import read_value


ALLOWED_QC_TYPES = (str, list, dict)


def q_writer(profile_name: str) -> str:
    clean = str(profile_name or "default").strip() or "default"
    return f"q:{clean}"


def profile_name_from_q_symbol(symbol: str) -> str:
    clean = str(symbol or "").strip()
    if clean.startswith("$Q."):
        head = clean.split(":", 1)[0]
        return head[3:] or "default"
    if clean.startswith("$q."):
        head = clean.split(":", 1)[0]
        return head[3:] or "default"
    if clean.startswith("$Q") or clean.startswith("$q"):
        return "default"
    return "default"


def deep_get(data: Any, path: str | None) -> Any:
    if path is None or path == "":
        return data

    cur = data
    for part in str(path).split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
            continue

        if isinstance(cur, list):
            try:
                idx = int(part)
            except Exception:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue

        return None

    return cur


def to_plain_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_THINK_EFFORT_VALUES = {"none", "minimal", "low", "medium", "high", "xhigh"}


def coerce_bool(value: Any, default: bool | None = None) -> bool | None:
    if value in (None, ""):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def normalize_think_value(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    if text in _THINK_EFFORT_VALUES:
        return text
    return default


def think_is_enabled(value: Any, default: bool | None = None) -> bool | None:
    normalized = normalize_think_value(value, default)
    if normalized is None:
        return default
    if isinstance(normalized, bool):
        return normalized
    if isinstance(normalized, str):
        return normalized not in {"none"}
    return default


def coerce_jsonish_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item)]

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception:
            return [text]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
        if isinstance(parsed, str) and parsed.strip():
            return [parsed.strip()]
        return []

    return [str(value)]


def normalize_path_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    out.append(item)
        return out

    return []


def extract_first_nonempty_scalar(payload: Any, paths: list[str]) -> str:
    for path in paths:
        value = deep_get(payload, path)

        if isinstance(value, str):
            if value != "":
                return value
            continue

        if value is None:
            continue

        if isinstance(value, (dict, list)):
            continue

        return str(value)

    return ""


def read_state_value(state, symbol: str, default):
    try:
        out = read_value(state, symbol, default)
    except Exception:
        return default

    if isinstance(out, dict) and "result" in out and "error" in out:
        if out.get("error"):
            return default
        value = out.get("result", default)
        return default if value is None else value

    return default if out is None else out


def unwrap_symbol_value(value: Any) -> Any:
    if isinstance(value, dict):
        keys = set(value.keys())
        if "result" in value and "error" in value and keys.issubset({"result", "error", "buffer_output", "ok"}):
            if value.get("error"):
                return None
            return value.get("result")
    return value


def parse_json_object(value: Any, *, key_name: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value in (None, ""):
        raise ValueError(f"{key_name} missing")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{key_name} missing")
        try:
            parsed = json.loads(text)
        except Exception as exc:
            raise ValueError(f"{key_name} must be valid JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{key_name} must be a JSON object")
        return parsed
    raise ValueError(f"{key_name} must be an object")


def merge_dicts(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            nested = dict(dst.get(key) or {})
            dst[key] = merge_dicts(nested, value)
        elif isinstance(value, dict):
            dst[key] = merge_dicts({}, value)
        else:
            dst[key] = value
    return dst


def clean_model_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"none", "null", "nil", "undefined", "false", "...", "n/a", "na", "<none>"}:
        return None
    return text
