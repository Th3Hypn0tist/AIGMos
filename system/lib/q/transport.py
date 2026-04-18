from __future__ import annotations

import json
from typing import Any, Iterable

from system.cs.lib.http_transport import HTTPTransportError, open_stream, request, request_json
from system.state.api import write_value

from .common import clean_model_value, q_writer, read_state_value
from .errors import QCallError
from .profile import resolve_model, resolve_timeout, ollama_model_from_api_key
from .providers import (
    build_payload,
    extract_stream_event,
    inline_thinking_active,
    new_inline_thinking_state,
    split_inline_think_tags,
)


def build_headers(profile: dict) -> dict:
    headers = dict(profile.get("headers") or {})
    api_key = str(profile.get("api_key") or "").strip()
    api_key_header = str(profile.get("api_key_header") or profile.get("auth_header") or "").strip()
    has_auth = any(str(k).lower() == "authorization" for k in headers.keys())
    ollama_model_from_authless_api_key = ollama_model_from_api_key(profile, profile.get("model"))

    if api_key:
        if api_key_header:
            headers[api_key_header] = api_key
        elif not has_auth and ollama_model_from_authless_api_key is None:
            headers["Authorization"] = f"Bearer {api_key}"

    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    return headers


def _is_model_required_error(exc: Exception) -> bool:
    return "model is required" in str(exc or "").lower()


def _force_payload_model(payload: dict, model: str | None) -> dict:
    out = dict(payload or {})
    clean = clean_model_value(model)
    if clean is not None:
        out["model"] = clean
    return out


def _debug_root(q_state_root: str | None) -> str:
    clean = str(q_state_root or "").strip()
    if not clean:
        return ""
    return f"{clean}:debug:transport"


def _debug_write(state, q_state_root: str | None, profile_name: str, key: str, value: Any) -> None:
    root = _debug_root(q_state_root)
    if state is None or not root:
        return
    try:
        write_value(state, f"{root}:{key}", value, writer=q_writer(profile_name), op="q_debug")
    except Exception:
        return


def _debug_append_raw_event(state, q_state_root: str | None, profile_name: str, event: Any) -> None:
    root = _debug_root(q_state_root)
    if state is None or not root:
        return
    key = f"{root}:raw_events"
    current = read_state_value(state, key, {})
    if not isinstance(current, dict):
        current = {}
    nums: list[int] = []
    for item_key in current.keys():
        try:
            nums.append(int(str(item_key)))
        except Exception:
            continue
    next_key = str(max(nums + [0]) + 1)
    current[next_key] = event
    try:
        write_value(state, key, current, writer=q_writer(profile_name), op="q_debug")
    except Exception:
        return


def _debug_reset(state, q_state_root: str | None, profile_name: str, *, endpoint: str, provider: str, payload: dict) -> None:
    _debug_write(state, q_state_root, profile_name, "endpoint", endpoint)
    _debug_write(state, q_state_root, profile_name, "provider", provider)
    _debug_write(state, q_state_root, profile_name, "request_payload", payload)
    _debug_write(state, q_state_root, profile_name, "raw_events", {})


def call_profile(
    profile: dict,
    prompt: str,
    role: str = "",
    chat: dict | None = None,
    *,
    state=None,
    profile_name: str = "default",
    think_value=None,
    q_state_root: str | None = None,
):
    endpoint = profile.get("base_url")
    timeout = resolve_timeout(profile, "timeout_seconds", state=state, profile_name=profile_name, required=True)
    headers = build_headers(profile)
    if not endpoint:
        raise QCallError("q profile base_url missing")

    payload = build_payload(
        profile,
        prompt,
        role,
        dict(chat or {}),
        stream=False,
        state=state,
        profile_name=profile_name,
        think_value=think_value,
    )
    provider = str(profile.get("provider") or "").strip().lower()
    _debug_reset(state, q_state_root, profile_name, endpoint=str(endpoint), provider=provider, payload=payload)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        return request_json("POST", endpoint, body=body, headers=headers, timeout=float(timeout), max_redirects=2)
    except HTTPTransportError as exc:
        if _is_model_required_error(exc):
            retry_model = resolve_model(profile, state, profile_name)
            forced_payload = _force_payload_model(payload, retry_model)
            if clean_model_value(forced_payload.get("model")) is not None and forced_payload != payload:
                _debug_write(state, q_state_root, profile_name, "request_payload", forced_payload)
                retry_body = json.dumps(forced_payload, ensure_ascii=False).encode("utf-8")
                try:
                    return request_json(
                        "POST",
                        endpoint,
                        body=retry_body,
                        headers=headers,
                        timeout=float(timeout),
                        max_redirects=2,
                    )
                except HTTPTransportError:
                    pass
        raise QCallError(f"q endpoint error: {exc}") from exc


def _iter_jsonl_events(resp) -> Iterable[Any]:
    while True:
        raw = resp.readline()
        if not raw:
            break
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            yield json.loads(text)
        except Exception:
            yield text


def _iter_sse_events(resp) -> Iterable[Any]:
    data_lines: list[str] = []
    while True:
        raw = resp.readline()
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if line == "":
            if not data_lines:
                continue
            payload_text = "\n".join(data_lines).strip()
            data_lines = []
            if payload_text == "[DONE]":
                break
            try:
                yield json.loads(payload_text)
            except Exception:
                yield payload_text
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())


def stream_profile(
    profile: dict,
    prompt: str,
    role: str = "",
    chat: dict | None = None,
    *,
    state=None,
    profile_name: str = "default",
    think_value=None,
    q_state_root: str | None = None,
) -> Iterable[dict[str, Any]]:
    endpoint = profile.get("base_url")
    connect_timeout = resolve_timeout(profile, "timeout_seconds", state=state, profile_name=profile_name, required=True)
    read_timeout = resolve_timeout(
        profile,
        "stream_timeout_seconds",
        state=state,
        profile_name=profile_name,
        default=None,
        required=False,
    )
    headers = build_headers(profile)
    if not endpoint:
        raise QCallError("q profile base_url missing")

    payload = build_payload(
        profile,
        prompt,
        role,
        dict(chat or {}),
        stream=True,
        state=state,
        profile_name=profile_name,
        think_value=think_value,
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    provider = str(profile.get("provider") or "").strip().lower()
    _debug_reset(state, q_state_root, profile_name, endpoint=str(endpoint), provider=provider, payload=payload)

    try:
        with open_stream(
            "POST",
            endpoint,
            body=body,
            headers=headers,
            connect_timeout=float(connect_timeout),
            read_timeout=None if read_timeout in (None, "") else float(read_timeout),
            max_redirects=2,
            tcp_keepalive=True,
        ) as resp:
            ctype = str(resp.headers.get("content-type") or "").lower()
            events = _iter_sse_events(resp) if "text/event-stream" in ctype else _iter_jsonl_events(resp)
            stream_message_tag = profile.get("stream_message_tag")
            chat_message_tag = profile.get("chat_message_tag")
            thinking_message_tag = profile.get("thinking_message_tag")
            inline_thinking_state = new_inline_thinking_state()
            allow_inline_thinking = bool(profile.get("inline_thinking_tags")) or provider == "ollama"
            saw_terminal_event = False

            for event in events:
                _debug_append_raw_event(state, q_state_root, profile_name, event)
                stream_event = extract_stream_event(
                    event,
                    stream_message_tag=stream_message_tag,
                    chat_message_tag=chat_message_tag,
                    thinking_message_tag=thinking_message_tag,
                    provider=provider,
                    inline_thinking_state=inline_thinking_state,
                    allow_inline_thinking=allow_inline_thinking,
                )
                error = str(stream_event.get("error") or "").strip()
                if error:
                    raise QCallError(f"q stream provider error: {error}")
                if int(stream_event.get("done") or 0) == 1:
                    saw_terminal_event = True
                if (
                    stream_event.get("content")
                    or stream_event.get("thinking")
                    or int(stream_event.get("done") or 0) == 1
                ):
                    yield stream_event

            if allow_inline_thinking and inline_thinking_active(inline_thinking_state):
                tail_thinking, tail_content = split_inline_think_tags("", inline_thinking_state, flush=True)
                if tail_content or tail_thinking:
                    yield {"content": tail_content, "thinking": tail_thinking, "done": 0, "error": "", "raw": ""}

            if not saw_terminal_event:
                raise QCallError("q stream ended without terminal done event")

    except HTTPTransportError as exc:
        raise QCallError(f"q endpoint error: {exc}") from exc


def health_q_profile(parser, profile_name: str) -> str:
    from .profile import get_profile

    profile = get_profile(parser, profile_name)
    health_url = str(profile.get("health_url") or "").strip()
    label = "q" if profile_name == "default" else f"q.{profile_name}"
    if not health_url:
        return f"[fail] {label} missing health_url"

    headers = build_headers(profile)
    timeout = resolve_timeout(profile, "timeout_seconds", state=parser.state, profile_name=profile_name, required=True)

    try:
        response = request("GET", health_url, headers=headers, timeout=float(timeout), max_bytes=65536, max_redirects=2)
    except Exception as exc:
        return f"[fail] {label} {exc}"

    if response.ok:
        return f"[ok] {label}"
    return f"[fail] {label} http {response.status}"


__all__ = ["build_headers", "call_profile", "health_q_profile", "stream_profile"]
