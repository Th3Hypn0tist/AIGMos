# system/config.py
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
STATE_DB_PATH = ROOT / "state.db"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise ValueError("missing config.json")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    validate_config(data)
    return data


def validate_config(data: dict) -> None:
    required_paths = [
        ("instance_name",),
        ("ip",),
        ("group",),
        ("role",),
        ("layout",),
        ("q", "default", "provider"),
        ("q", "default", "base_url"),
        ("q", "default", "api_key"),
        ("q", "default", "model"),
        ("q", "default", "timeout_seconds"),
        ("osc", "in", "bind_ip"),
        ("osc", "in", "port"),
        ("osc", "in", "buffer"),
    ]

    for path in required_paths:
        value = _get_required(data, path)
        if value is None:
            raise ValueError(f"missing config key: {'.'.join(path)}")
        if isinstance(value, str) and value == "" and path[-1] != "api_key":
            raise ValueError(f"empty config key: {'.'.join(path)}")

    _validate_q_profiles(data.get("q"))


def _validate_q_profiles(qcfg: dict) -> None:
    if not isinstance(qcfg, dict):
        raise ValueError("missing config key: q")

    default = qcfg.get("default")
    if not isinstance(default, dict):
        raise ValueError("missing config key: q.default")

    required_profile_keys = (
        "provider",
        "base_url",
        "api_key",
        "model",
        "timeout_seconds",
    )

    for profile_name, profile in qcfg.items():
        if not isinstance(profile, dict):
            raise ValueError(f"q profile must be object: q.{profile_name}")

        for key in required_profile_keys:
            if key not in profile:
                raise ValueError(f"missing config key: q.{profile_name}.{key}")
            value = profile[key]
            if value is None:
                raise ValueError(f"missing config key: q.{profile_name}.{key}")
            if isinstance(value, str) and value == "" and key != "api_key":
                raise ValueError(f"empty config key: q.{profile_name}.{key}")


def require_osc_in_config(state) -> tuple[str, int, int]:
    bind_ip = state.get("#SYSTEM:config:osc:in:bind_ip")
    port = state.get("#SYSTEM:config:osc:in:port")
    buffer_size = state.get("#SYSTEM:config:osc:in:buffer")

    if bind_ip["error"] or bind_ip["result"] in (None, ""):
        raise ValueError("missing #SYSTEM:config:osc:in:bind_ip")
    if port["error"] or port["result"] is None:
        raise ValueError("missing #SYSTEM:config:osc:in:port")
    if buffer_size["error"] or buffer_size["result"] is None:
        raise ValueError("missing #SYSTEM:config:osc:in:buffer")

    return str(bind_ip["result"]), int(port["result"]), int(buffer_size["result"])


def _get_required(data: dict, path: tuple[str, ...]):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            raise ValueError(f"missing config key: {'.'.join(path)}")
        cur = cur[key]
    return cur
