from __future__ import annotations

import json
import re
from typing import Any

from .common import (
    ALLOWED_QC_TYPES,
    coerce_bool,
    extract_first_nonempty_scalar,
    normalize_path_list,
    deep_get,
    to_plain_string,
    think_is_enabled,
    merge_dicts,
)
from .errors import QCallError
from .profile import resolve_model, resolve_think_value
from .sampler import resolve_q_sampler_values


_DEFAULT_RESPONSE_PATHS = (
    "response",
    "message.content",
    "message",
    "choices.0.message.content",
    "content",
)

_DEFAULT_STREAM_PATHS = (
    "response",
    "choices.0.delta.content",
    "delta.content",
    "message.content",
    "choices.0.message.content",
    "content",
)

_DEFAULT_THINKING_PATHS = (
    "message.thinking",
    "thinking",
    "choices.0.delta.reasoning_content",
    "delta.reasoning_content",
    "choices.0.message.reasoning_content",
    "message.reasoning_content",
    "reasoning_content",
)

_INLINE_THINK_OPEN = "<think>"
_INLINE_THINK_CLOSE = "</think>"
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_TAG_RE = re.compile(r"</?think>", re.IGNORECASE)


def _apply_profile_think_payload(payload: dict[str, Any], profile: dict, think_value: Any) -> None:
    enabled = think_is_enabled(think_value, None)
    if enabled is None:
        return

    key = 'think_payload' if enabled else 'nothink_payload'
    fragment = profile.get(key)
    if not isinstance(fragment, dict):
        raise QCallError(f'q profile {key} missing or invalid')
    if not fragment:
        return
    merge_dicts(payload, dict(fragment))


def chat_to_provider_messages(role: str, chat: dict, prompt: str) -> list[dict]:
    messages: list[dict] = []
    if role.strip():
        messages.append({"role": "system", "content": role})
    rows: list[tuple[int, dict]] = []
    for key, value in chat.items():
        if not isinstance(value, dict):
            continue
        try:
            idx = int(str(key))
        except Exception:
            continue
        rows.append((idx, value))
    rows.sort(key=lambda x: x[0])
    for _, item in rows:
        item_prompt = str(item.get("prompt") or "")
        item_response = str(item.get("response") or "")
        if item_prompt:
            messages.append({"role": "user", "content": item_prompt})
        if item_response:
            messages.append({"role": "assistant", "content": item_response})
    messages.append({"role": "user", "content": prompt})
    return messages


def build_payload(profile: dict, prompt: str, role: str, chat: dict, stream: bool = False, *, state=None, profile_name: str = "default", think_value: Any = None):
    provider = str(profile.get("provider") or "").strip().lower()
    base_url = str(profile.get("base_url") or "").strip().lower()
    model = resolve_model(profile, state, profile_name)
    sampler = resolve_q_sampler_values(profile, state, profile_name)
    if think_value is None:
        think_value = resolve_think_value(profile, state, profile_name)

    if provider == "ollama" or "/api/chat" in base_url or base_url.endswith("/api/chat"):
        if model in (None, ""):
            raise QCallError("model is required")
        payload = {"model": model, "messages": chat_to_provider_messages(role, chat, prompt), "stream": stream}
        _apply_profile_think_payload(payload, profile, think_value)
        options: dict[str, Any] = {}
        for key in ("temperature", "top_k", "top_p", "repeat_penalty"):
            if key in sampler:
                options[key] = sampler[key]
        if "max_tokens" in sampler:
            options["num_predict"] = sampler["max_tokens"]
        if "seed" in sampler:
            options["seed"] = sampler["seed"]
        if "num_ctx" in sampler:
            options["num_ctx"] = sampler["num_ctx"]
        if options:
            payload["options"] = options
        return payload

    if "/chat/completions" in base_url or provider in {"openai", "openrouter"}:
        if model in (None, ""):
            raise QCallError("model is required")
        payload = {"model": model, "messages": chat_to_provider_messages(role, chat, prompt), "stream": stream}
        if "temperature" in sampler:
            payload["temperature"] = sampler["temperature"]
        if "top_p" in sampler:
            payload["top_p"] = sampler["top_p"]
        if "max_tokens" in sampler:
            payload["max_tokens"] = sampler["max_tokens"]
        if "seed" in sampler:
            payload["seed"] = sampler["seed"]
        _apply_profile_think_payload(payload, profile, think_value)
        return payload

    payload = {"prompt": prompt, "role": role, "chat": chat}
    if model not in (None, ""):
        payload["model"] = model
    if stream:
        payload["stream"] = True
    for key in ("temperature", "top_k", "top_p", "repeat_penalty", "max_tokens", "seed", "num_ctx"):
        if key in sampler:
            payload[key] = sampler[key]
    _apply_profile_think_payload(payload, profile, think_value)
    return payload


def extract_raw_value(payload, chat_message_tag: str | list[str] | None):
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (dict, list)):
        for path in normalize_path_list(chat_message_tag):
            value = deep_get(payload, path)
            if value is not None:
                return value
        for path in _DEFAULT_RESPONSE_PATHS:
            value = deep_get(payload, path)
            if value is not None:
                return value
        return payload
    raise QCallError(f"unsupported q response type: {type(payload).__name__}")


def _stream_error_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    payload_type = str(payload.get("type") or "").strip().lower()
    if payload_type == "error":
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            for key in ("message", "detail", "type"):
                value = error_obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(error_obj, ensure_ascii=False)
        if isinstance(error_obj, str) and error_obj.strip():
            return error_obj.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    if "error" in payload:
        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            for key in ("message", "detail", "type"):
                value = error_obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(error_obj, ensure_ascii=False)
        if isinstance(error_obj, str) and error_obj.strip():
            return error_obj.strip()
    return ""


def _is_terminal_stream_event(payload: Any, provider: str = "") -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("done") is True:
        return True
    payload_type = str(payload.get("type") or "").strip().lower()
    provider = str(provider or "").strip().lower()
    if payload_type in {"message_stop", "response.completed", "response.complete", "completion.stop"}:
        return True
    if provider == "anthropic" and payload_type == "message_delta":
        stop_reason = payload.get("stop_reason")
        if isinstance(stop_reason, str) and stop_reason.strip():
            return True
    finish_reason = deep_get(payload, "choices.0.finish_reason")
    if isinstance(finish_reason, str) and finish_reason.strip():
        return True
    stop_reason = payload.get("stop_reason")
    if isinstance(stop_reason, str) and stop_reason.strip():
        return True
    return False


def _thinking_paths(thinking_message_tag: str | list[str] | None) -> list[str]:
    paths: list[str] = []
    paths.extend(normalize_path_list(thinking_message_tag))
    for path in _DEFAULT_THINKING_PATHS:
        if path not in paths:
            paths.append(path)
    return paths


def _content_paths(stream_message_tag: str | list[str] | None, chat_message_tag: str | list[str] | None) -> list[str]:
    paths: list[str] = []
    paths.extend(normalize_path_list(stream_message_tag))
    paths.extend(normalize_path_list(chat_message_tag))
    for path in _DEFAULT_STREAM_PATHS:
        if path not in paths:
            paths.append(path)
    return paths


def new_inline_thinking_state() -> dict[str, Any]:
    return {"buffer": "", "is_thinking": False}


def inline_thinking_active(state: dict[str, Any] | None) -> bool:
    if not isinstance(state, dict):
        return False
    return bool(state.get("buffer") or state.get("is_thinking"))


def strip_inline_think_markup(text: Any) -> str:
    value = str(text or "")
    if not value:
        return ""
    value = _THINK_BLOCK_RE.sub("", value)
    value = _THINK_TAG_RE.sub("", value)
    return value


def _partial_suffix_len(buf: str, token: str) -> int:
    text = str(buf or "")
    tag = str(token or "")
    if not text or not tag:
        return 0
    max_len = min(len(text), len(tag) - 1)
    for size in range(max_len, 0, -1):
        if text.endswith(tag[:size]):
            return size
    return 0


def split_inline_think_tags(text: str, state: dict[str, Any] | None, *, flush: bool = False) -> tuple[str, str]:
    if state is None:
        state = new_inline_thinking_state()
    buffer = str(state.get("buffer") or "") + str(text or "")
    is_thinking = 1 if state.get("is_thinking") else 0
    thinking_parts: list[str] = []
    content_parts: list[str] = []
    while True:
        if is_thinking:
            end = buffer.find(_INLINE_THINK_CLOSE)
            if end == -1:
                if flush:
                    if buffer:
                        thinking_parts.append(buffer)
                    buffer = ""
                else:
                    keep = _partial_suffix_len(buffer, _INLINE_THINK_CLOSE)
                    emit = buffer[:-keep] if keep > 0 else buffer
                    if emit:
                        thinking_parts.append(emit)
                    buffer = buffer[-keep:] if keep > 0 else ""
                break
            emit = buffer[:end]
            if emit:
                thinking_parts.append(emit)
            buffer = buffer[end + len(_INLINE_THINK_CLOSE):]
            is_thinking = 0
            continue
        start = buffer.find(_INLINE_THINK_OPEN)
        if start == -1:
            if flush:
                if buffer:
                    content_parts.append(buffer)
                buffer = ""
            else:
                keep = _partial_suffix_len(buffer, _INLINE_THINK_OPEN)
                emit = buffer[:-keep] if keep > 0 else buffer
                if emit:
                    content_parts.append(emit)
                buffer = buffer[-keep:] if keep > 0 else ""
            break
        emit = buffer[:start]
        if emit:
            content_parts.append(emit)
        buffer = buffer[start + len(_INLINE_THINK_OPEN):]
        is_thinking = 1
    state["buffer"] = buffer
    state["is_thinking"] = bool(is_thinking)
    return "".join(thinking_parts), "".join(content_parts)


def _same_visible_text(left: Any, right: Any) -> bool:
    a = strip_inline_think_markup(left).strip()
    b = strip_inline_think_markup(right).strip()
    return bool(a) and bool(b) and a == b


def extract_stream_event(payload, stream_message_tag: str | list[str] | None, chat_message_tag: str | list[str] | None, thinking_message_tag: str | list[str] | None = None, *, provider: str = "", inline_thinking_state: dict[str, Any] | None = None, allow_inline_thinking: bool = False) -> dict[str, Any]:
    error = ""
    if isinstance(payload, str):
        content = payload
        thinking = ""
        done = 0
        raw = payload
    elif not isinstance(payload, dict):
        content = ""
        thinking = ""
        done = 0
        raw = payload
    else:
        error = _stream_error_message(payload)
        thinking = extract_first_nonempty_scalar(payload, _thinking_paths(thinking_message_tag))
        content = extract_first_nonempty_scalar(payload, _content_paths(stream_message_tag, chat_message_tag))
        done = 1 if _is_terminal_stream_event(payload, provider=provider) else 0
        raw = payload

    if allow_inline_thinking and (content or done == 1 or inline_thinking_active(inline_thinking_state)):
        inline_thinking, inline_content = split_inline_think_tags(content, inline_thinking_state, flush=(done == 1))
        content = inline_content
        if inline_thinking:
            thinking = thinking + inline_thinking if thinking else inline_thinking
        elif done == 1 and inline_thinking_active(inline_thinking_state):
            flushed_thinking, flushed_content = split_inline_think_tags("", inline_thinking_state, flush=True)
            if flushed_thinking:
                thinking = thinking + flushed_thinking if thinking else flushed_thinking
            if flushed_content:
                content = content + flushed_content if content else flushed_content

    if thinking and content and _same_visible_text(thinking, content):
        content = ""

    content = strip_inline_think_markup(content)
    thinking = strip_inline_think_markup(thinking)
    return {"content": content, "thinking": thinking, "done": done, "error": error, "raw": raw}


def extract_chat(payload, chat_message_tag: str | list[str] | None) -> str:
    value = extract_raw_value(payload, chat_message_tag)
    return to_plain_string(value)


def _maybe_parse_json_string(value: str):
    text = value.strip()
    if not text:
        return value
    try:
        parsed = json.loads(text)
    except Exception:
        return value
    if isinstance(parsed, ALLOWED_QC_TYPES):
        return parsed
    return value


def decode_qc_output(payload, chat_message_tag: str | list[str] | None):
    value = extract_raw_value(payload, chat_message_tag)
    if isinstance(value, str):
        value = _maybe_parse_json_string(value)
    if not isinstance(value, ALLOWED_QC_TYPES):
        raise QCallError("qc accepts only string, list or dict")
    return value


def profile_has_stream(profile: dict) -> bool:
    stream_flag = coerce_bool(profile.get("stream"), None)
    if stream_flag is False:
        return False
    if stream_flag is True:
        return True
    return len(normalize_path_list(profile.get("stream_message_tag"))) > 0


__all__ = [
    "build_payload",
    "decode_qc_output",
    "extract_chat",
    "extract_stream_event",
    "inline_thinking_active",
    "new_inline_thinking_state",
    "profile_has_stream",
    "split_inline_think_tags",
    "strip_inline_think_markup",
]
