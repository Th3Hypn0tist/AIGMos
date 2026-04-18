from __future__ import annotations

import json
from typing import Any

from system.cs.runtime_ctx import get_runtime, runtime_map, set_runtime

from .common import clean_model_value, coerce_bool, normalize_think_value, think_is_enabled, read_state_value, parse_json_object
from .errors import QCallError
from .symbols import (
    chat_symbol_for_profile,
    chat_symbol_for_runtime,
    q_state_prefix_for_state,
    response_symbol_for_profile,
    response_symbol_for_runtime,
    role_symbol_for_profile,
    role_symbol_for_runtime,
    system_prompt_symbol_for_profile,
    system_prompt_symbol_for_runtime,
    thinking_symbol_for_profile,
    thinking_symbol_for_runtime,
)

from .params import collect_q_overrides


_PROFILE_KEYS = (
    "base_url",
    "url",
    "endpoint",
    "model",
    "provider",
    "headers",
    "api_key",
    "api_key_header",
    "auth_header",
    "stream",
    "timeout_seconds",
    "stream_timeout_seconds",
    "stream_message_tag",
    "chat_message_tag",
    "message_tag",
    "thinking_message_tag",
    "thinking_tag",
    "health_url",
    "think",
    "thinking",
    "temperature",
    "top_k",
    "top_p",
    "repeat_penalty",
    "max_tokens",
    "seed",
    "num_ctx",
    "inline_thinking_tags",
    "think_payload",
    "nothink_payload",
)


def read_state_override(state, symbol: str):
    value = read_state_value(state, symbol, None)
    return None if value in (None, "") else value


def read_q_override(state, profile_name: str, key: str):
    candidates: list[str] = []
    runtime_prefix = q_state_prefix_for_state(state, profile_name)
    clean_key = str(key or '').strip()

    if runtime_prefix:
        if runtime_prefix.startswith('|') and ':' in runtime_prefix:
            role_key = 'think' if clean_key == 'thinking' else clean_key
            if clean_key == 'role':
                candidates.append(f"{runtime_prefix}:role:name")
            elif clean_key == 'system_prompt':
                candidates.append(f"{runtime_prefix}:role:system_prompt")
            elif role_key:
                candidates.append(f"{runtime_prefix}:role:{role_key}")
        else:
            candidates.append(f"{runtime_prefix}:{clean_key}")

    if profile_name and profile_name != "default":
        candidates.append(f"$Q.{profile_name}:{clean_key}")
    candidates.append(f"$Q:{clean_key}")

    seen: set[str] = set()
    for symbol in candidates:
        if symbol in seen:
            continue
        seen.add(symbol)
        value = read_state_override(state, symbol)
        if value not in (None, ""):
            return value

    return None


def _read_profile_state_map(state, profile_name: str) -> dict[str, Any]:
    if state is None:
        return {}

    out: dict[str, Any] = {}

    prefixes = ["#SYSTEM:config:q", "#SYSTEM:config:q:default"]
    if profile_name and profile_name != "default":
        prefixes.append(f"#SYSTEM:config:q:{profile_name}")

    for prefix in prefixes:
        for key in _PROFILE_KEYS:
            value = read_state_value(state, f"{prefix}:{key}", None)
            if value not in (None, ""):
                out[key] = value

    return out


def _normalize_profile(profile: dict) -> dict:
    merged = dict(profile)

    base_url = str(merged.get("base_url") or merged.get("url") or merged.get("endpoint") or "").strip()
    if base_url:
        merged["base_url"] = base_url

    headers = merged.get("headers")
    if isinstance(headers, str):
        try:
            headers = json.loads(headers)
        except Exception:
            headers = {}
    if not isinstance(headers, dict):
        headers = {}
    merged["headers"] = headers

    if merged.get("chat_message_tag") in (None, "") and merged.get("message_tag") not in (None, ""):
        merged["chat_message_tag"] = merged.get("message_tag")

    if merged.get("thinking_message_tag") in (None, "") and merged.get("thinking_tag") not in (None, ""):
        merged["thinking_message_tag"] = merged.get("thinking_tag")

    for key in ("think_payload", "nothink_payload"):
        if key not in merged:
            continue
        merged[key] = parse_json_object(merged.get(key), key_name=key)

    merged["stream"] = coerce_bool(merged.get("stream"), False)
    merged["inline_thinking_tags"] = coerce_bool(merged.get("inline_thinking_tags"), False)

    merged["model"] = clean_model_value(merged.get("model"))
    provider = merged.get("provider")
    merged["provider"] = "" if provider in (None, "") else str(provider).strip()
    return merged


def _read_q_timeout_from_state(state, profile_name: str, key: str):
    if state is None:
        return None

    direct = read_q_override(state, profile_name, key)
    if direct not in (None, ""):
        return direct

    candidates = []
    if profile_name and profile_name != "default":
        candidates.append(f"#SYSTEM:config:q:{profile_name}:{key}")
    candidates.extend([
        f"#SYSTEM:config:q:default:{key}",
        f"#SYSTEM:config:q:{key}",
    ])

    for symbol in candidates:
        value = read_state_value(state, symbol, None)
        if value not in (None, ""):
            return value

    return None


def resolve_timeout(profile: dict, *keys: str, state=None, profile_name: str = "default", default=None, required: bool = False):
    for key in keys:
        raw = _read_q_timeout_from_state(state, profile_name, key)
        if raw in (None, ""):
            raw = profile.get(key)
        if raw in (None, ""):
            continue
        try:
            value = float(raw)
        except Exception as exc:
            raise QCallError(f"invalid timeout value for {key}: {raw}") from exc
        if value <= 0:
            raise QCallError(f"invalid timeout value for {key}: must be > 0")
        return value

    if required:
        joined = ", ".join(keys)
        raise QCallError(f"q timeout missing for ({joined})")

    return default


def model_from_runtime_config(profile: dict, profile_name: str) -> str | None:
    config = profile.get("__runtime_config__")
    if not isinstance(config, dict):
        return None

    qcfg = config.get("q")
    if not isinstance(qcfg, dict):
        return None

    ordered: list[dict] = []
    if profile_name and profile_name != "default":
        cfg = qcfg.get(profile_name)
        if isinstance(cfg, dict):
            ordered.append(cfg)
    cfg = qcfg.get("default")
    if isinstance(cfg, dict):
        ordered.append(cfg)

    for cfg in ordered:
        clean = clean_model_value(cfg.get("model"))
        if clean is not None:
            return clean

    return None


def ollama_model_from_api_key(profile: dict, current_model: Any = None) -> str | None:
    provider = str(profile.get("provider") or "").strip().lower()
    base_url = str(profile.get("base_url") or "").strip().lower()
    api_key = clean_model_value(profile.get("api_key"))
    api_key_header = str(profile.get("api_key_header") or profile.get("auth_header") or "").strip()
    headers = profile.get("headers") if isinstance(profile.get("headers"), dict) else {}
    has_auth = any(str(k).lower() == "authorization" for k in headers.keys())
    model_text = clean_model_value(current_model)

    if provider != "ollama":
        return None
    if not ("/api/chat" in base_url or base_url.endswith("/api/chat")):
        return None
    if api_key is None or ":" not in api_key:
        return None
    if api_key_header or has_auth:
        return None

    if model_text is None:
        return api_key
    if ":" in model_text:
        return None
    if len(model_text) <= 2:
        return api_key
    return None


def resolve_model(profile: dict, state, profile_name: str) -> str | None:
    direct_candidates: list[str] = []

    for symbol_value in (read_q_override(state, profile_name, "model"), profile.get("model")):
        clean = clean_model_value(symbol_value)
        if clean is not None:
            direct_candidates.append(clean)

    runtime_profile = {}
    runtime_default = {}
    config = profile.get("__runtime_config__")
    if isinstance(config, dict):
        runtime_q = config.get("q")
        if isinstance(runtime_q, dict):
            runtime_default = runtime_q.get("default") if isinstance(runtime_q.get("default"), dict) else {}
            runtime_profile = runtime_q.get(profile_name) if isinstance(runtime_q.get(profile_name), dict) else {}

    for cfg in (runtime_profile, runtime_default):
        clean = clean_model_value(cfg.get("model") if isinstance(cfg, dict) else None)
        if clean is not None:
            direct_candidates.append(clean)

    for symbol in (
        f"#SYSTEM:config:q:{profile_name}:model" if profile_name and profile_name != "default" else "",
        "#SYSTEM:config:q:default:model",
        "#SYSTEM:config:q:model",
    ):
        if not symbol:
            continue
        clean = clean_model_value(read_state_value(state, symbol, None))
        if clean is not None:
            direct_candidates.append(clean)

    for candidate in direct_candidates:
        derived_model = ollama_model_from_api_key(profile, candidate)
        if derived_model is not None:
            return derived_model
        return candidate

    derived_model = ollama_model_from_api_key(profile, None)
    if derived_model is not None:
        return derived_model

    configured_model = model_from_runtime_config(profile, profile_name)
    if configured_model is not None:
        derived_model = ollama_model_from_api_key(profile, configured_model)
        if derived_model is not None:
            return derived_model
        return configured_model

    return None


def resolve_think_value(profile: dict, state, profile_name: str):
    override = read_q_override(state, profile_name, "think")
    if override not in (None, ""):
        return normalize_think_value(override, None)

    override = read_q_override(state, profile_name, "thinking")
    if override not in (None, ""):
        return normalize_think_value(override, None)

    if "think" in profile:
        return normalize_think_value(profile.get("think"), None)
    if "thinking" in profile:
        return normalize_think_value(profile.get("thinking"), None)
    return None


def resolve_thinking_flag(profile: dict, state, profile_name: str) -> bool | None:
    return think_is_enabled(resolve_think_value(profile, state, profile_name), None)


def get_profile(parser, profile_name: str) -> dict:
    runtime = runtime_map(parser)
    config = runtime.get("config") or {}
    qcfg = config.get("q") or {}

    default_profile = qcfg.get("default")
    if not isinstance(default_profile, dict):
        default_profile = {}

    specific_profile = qcfg.get(profile_name)
    if not isinstance(specific_profile, dict):
        specific_profile = {}

    profile = dict(default_profile)
    profile.update(specific_profile)
    profile.update(_read_profile_state_map(getattr(parser, "state", None), profile_name))
    profile["__runtime_config__"] = config

    if callable(collect_q_overrides):
        try:
            overrides = collect_q_overrides(parser, profile_name) or {}
        except Exception:
            overrides = {}
        if isinstance(overrides, dict):
            if overrides.get("model") not in (None, ""):
                profile["model"] = overrides["model"]
            if overrides.get("timeout_seconds") not in (None, ""):
                profile["timeout_seconds"] = overrides["timeout_seconds"]
            if overrides.get("stream_timeout_seconds") not in (None, ""):
                profile["stream_timeout_seconds"] = overrides["stream_timeout_seconds"]
            if overrides.get("stream") is not None:
                profile["stream"] = overrides["stream"]
            if overrides.get("think") not in (None, ""):
                profile["think"] = overrides["think"]
            elif overrides.get("thinking") not in (None, ""):
                profile["think"] = overrides["thinking"]
            if overrides.get("heat") not in (None, ""):
                profile["temperature"] = overrides["heat"]
            if overrides.get("top_k") not in (None, ""):
                profile["top_k"] = overrides["top_k"]
            if overrides.get("top_p") not in (None, ""):
                profile["top_p"] = overrides["top_p"]
            if overrides.get("repeat_penalty") not in (None, ""):
                profile["repeat_penalty"] = overrides["repeat_penalty"]
            if overrides.get("max_tokens") not in (None, ""):
                profile["max_tokens"] = overrides["max_tokens"]
            if overrides.get("seed") not in (None, ""):
                profile["seed"] = overrides["seed"]
            if overrides.get("num_ctx") not in (None, ""):
                profile["num_ctx"] = overrides["num_ctx"]

    try:
        profile = _normalize_profile(profile)
    except ValueError as exc:
        raise QCallError(f"invalid q profile {profile_name}: {exc}") from exc

    if not isinstance(profile, dict) or not profile:
        raise QCallError(f"unknown q profile: {profile_name}")
    if not profile.get("base_url"):
        raise QCallError(f"q profile base_url missing: {profile_name}")
    for key in ("think_payload", "nothink_payload"):
        if key not in profile:
            raise QCallError(f"q profile {key} missing: {profile_name}")
        if not isinstance(profile.get(key), dict):
            raise QCallError(f"q profile {key} must be an object: {profile_name}")

    return profile


def get_active_profile(parser) -> str:
    value = get_runtime(parser, "q_profile", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "default"


def set_active_profile(parser, profile_name: str) -> None:
    get_profile(parser, profile_name)
    set_runtime(parser, "q_profile", profile_name)
    set_runtime(parser, "q_chat_symbol", chat_symbol_for_runtime(parser, profile_name))
    set_runtime(parser, "q_response_symbol", response_symbol_for_runtime(parser, profile_name))
    set_runtime(parser, "q_thinking_symbol", thinking_symbol_for_runtime(parser, profile_name))
    set_runtime(parser, "q_role_symbol", role_symbol_for_runtime(parser, profile_name))
    set_runtime(parser, "q_system_prompt_symbol", system_prompt_symbol_for_runtime(parser, profile_name))


def resolve_profile_name(parser, command_token: str, base_command: str) -> str:
    if command_token == base_command:
        active = get_active_profile(parser)
        try:
            profile = get_profile(parser, active)
        except Exception:
            return "default"
        if clean_model_value(profile.get("model")) is None:
            configured_model = model_from_runtime_config(profile, active)
            if configured_model is not None:
                return active
            if active != "default":
                try:
                    get_profile(parser, "default")
                    return "default"
                except Exception:
                    pass
        return active

    prefix = base_command + "."
    if not command_token.startswith(prefix):
        raise QCallError(f"usage: {base_command}[.<profile>] ...")

    profile_name = command_token[len(prefix):].strip()
    if not profile_name:
        raise QCallError(f"missing {base_command} profile")

    get_profile(parser, profile_name)
    return profile_name


__all__ = [
    "get_profile",
    "get_active_profile",
    "set_active_profile",
    "resolve_profile_name",
    "read_state_override",
    "read_q_override",
    "resolve_timeout",
    "resolve_model",
    "resolve_think_value",
    "resolve_thinking_flag",
    "model_from_runtime_config",
    "ollama_model_from_api_key",
]
