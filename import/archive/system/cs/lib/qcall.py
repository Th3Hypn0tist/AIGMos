# system/cs/lib/qcall.py
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable


_ALLOWED_QC_TYPES = (str, list, dict)

_FALLBACK_PATHS = (
    "response",
    "message.content",
    "message",
    "choices.0.message.content",
    "content",
)

_STREAM_FALLBACK_PATHS = (
    "response",
    "choices.0.delta.content",
    "delta.content",
    "message.content",
    "choices.0.message.content",
    "content",
)


class QCallError(Exception):
    pass


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


def _normalize_path_list(value: Any) -> list[str]:
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


def _extract_first_nonempty_scalar(payload: Any, paths: list[str]) -> str:
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


def build_headers(profile: dict) -> dict:
    headers = dict(profile.get("headers") or {})
    api_key = str(profile.get("api_key") or "").strip()
    has_auth = any(str(k).lower() == "authorization" for k in headers.keys())

    if api_key and not has_auth:
        headers["Authorization"] = f"Bearer {api_key}"

    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    return headers


def get_profile(parser, profile_name: str) -> dict:
    runtime = getattr(parser, "runtime", None)
    if not isinstance(runtime, dict):
        raise QCallError("parser.runtime missing")

    config = runtime.get("config") or {}
    qcfg = config.get("q") or {}
    profile = qcfg.get(profile_name)

    if not isinstance(profile, dict):
        raise QCallError(f"unknown q profile: {profile_name}")

    return profile


def get_active_profile(parser) -> str:
    runtime = getattr(parser, "runtime", None)
    if isinstance(runtime, dict):
        value = runtime.get("q_profile")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "default"


def chat_symbol_for_profile(profile_name: str) -> str:
    if profile_name == "default":
        return "$CH:q"
    return f"$CH:{profile_name}"


def get_active_chat_symbol(parser) -> str:
    runtime = getattr(parser, "runtime", None)
    if isinstance(runtime, dict):
        value = runtime.get("q_chat_symbol")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return chat_symbol_for_profile(get_active_profile(parser))


def system_prompt_symbol_for_profile(profile_name: str) -> str:
    if profile_name == "default":
        return "#SYSTEM:profiles:q:system_prompt"
    return f"#SYSTEM:profiles:{profile_name}:system_prompt"


def set_active_profile(parser, profile_name: str) -> None:
    runtime = getattr(parser, "runtime", None)
    if not isinstance(runtime, dict):
        runtime = {}
        parser.runtime = runtime

    get_profile(parser, profile_name)
    runtime["q_profile"] = profile_name
    runtime["q_chat_symbol"] = chat_symbol_for_profile(profile_name)


def resolve_profile_name(parser, command_token: str, base_command: str) -> str:
    if command_token == base_command:
        return get_active_profile(parser)

    prefix = base_command + "."
    if not command_token.startswith(prefix):
        raise QCallError(f"usage: {base_command}[.<profile>] ...")

    profile_name = command_token[len(prefix):].strip()
    if not profile_name:
        raise QCallError(f"missing {base_command} profile")

    get_profile(parser, profile_name)
    return profile_name


def _next_chat_key(chat: dict) -> str:
    max_num = 0
    for key in chat.keys():
        try:
            max_num = max(max_num, int(str(key)))
        except Exception:
            continue
    return str(max_num + 1)


def _normalize_legacy_turns(current: dict) -> dict:
    turns = current.get("turns")
    if not isinstance(turns, list):
        return {}

    out: dict[str, dict] = {}
    idx = 1

    for turn in turns:
        if not isinstance(turn, dict):
            continue

        q_text = deep_get(turn, "q.text")
        a_text = deep_get(turn, "a.text")

        out[str(idx)] = {
            "prompt": q_text if isinstance(q_text, str) else "",
            "response": a_text if isinstance(a_text, str) else "",
            "done": 1,
        }
        idx += 1

    return out


def load_chat(state, symbol: str) -> dict:
    out = state.get(symbol)
    if out["error"]:
        raise QCallError(out["error"])

    current = out["result"]
    if not isinstance(current, dict):
        return {}

    if "turns" in current:
        return _normalize_legacy_turns(current)

    clean: dict[str, dict] = {}
    for key, value in current.items():
        if not isinstance(value, dict):
            continue

        prompt = value.get("prompt")
        response = value.get("response")
        done = value.get("done")

        clean[str(key)] = {
            "prompt": prompt if isinstance(prompt, str) else "",
            "response": response if isinstance(response, str) else "",
            "done": 1 if done else 0,
        }

    return clean


def save_chat(state, symbol: str, chat: dict) -> None:
    out = state.set(symbol, chat)
    if out["error"]:
        raise QCallError(out["error"])


def open_chat_entry(state, symbol: str, prompt: str) -> str:
    chat = load_chat(state, symbol)
    key = _next_chat_key(chat)
    chat[key] = {
        "prompt": prompt,
        "response": "",
        "done": 0,
    }
    save_chat(state, symbol, chat)
    return key


def append_chat_chunk(state, symbol: str, key: str, chunk: str) -> str:
    chat = load_chat(state, symbol)
    item = chat.get(key)
    if not isinstance(item, dict):
        raise QCallError(f"chat entry missing: {symbol}:{key}")

    item["response"] = str(item.get("response") or "") + chunk
    item["done"] = 0
    chat[key] = item
    save_chat(state, symbol, chat)
    return str(item["response"])


def close_chat_entry(state, symbol: str, key: str) -> dict:
    chat = load_chat(state, symbol)
    item = chat.get(key)
    if not isinstance(item, dict):
        raise QCallError(f"chat entry missing: {symbol}:{key}")

    item["done"] = 1
    chat[key] = item
    save_chat(state, symbol, chat)
    return item


def write_full_chat_entry(state, symbol: str, prompt: str, response: str) -> dict:
    key = open_chat_entry(state, symbol, prompt)
    if response:
        append_chat_chunk(state, symbol, key, response)
    item = close_chat_entry(state, symbol, key)

    return {
        "chat_key": key,
        "item": item,
        "message": str(item.get("response") or ""),
    }


def get_system_prompt(parser, profile_name: str) -> str:
    symbol = system_prompt_symbol_for_profile(profile_name)
    out = parser.state.get(symbol)
    if out["error"]:
        return ""

    value = out["result"]
    if value is None:
        return ""
    return str(value)


def chat_to_messages(chat: dict, system_prompt: str = "") -> list[dict]:
    messages: list[dict] = []

    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})

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
        prompt = str(item.get("prompt") or "")
        response = str(item.get("response") or "")

        if prompt:
            messages.append({"role": "user", "content": prompt})
        if response:
            messages.append({"role": "assistant", "content": response})

    return messages


def is_target_token(token: str) -> bool:
    return isinstance(token, str) and token[:1] in "$#&"


def expand_prompt_tokens(parser, tokens: list[str]) -> str:
    expanded = []

    for token in tokens:
        if is_target_token(token):
            out = parser.state.get(token)
            if out["error"]:
                raise QCallError(out["error"])

            value = out["result"]
            if isinstance(value, (dict, list)):
                expanded.append(json.dumps(value, ensure_ascii=False))
            elif value is None:
                expanded.append("null")
            else:
                expanded.append(str(value))
            continue

        expanded.append(token)

    return " ".join(expanded).strip()


def _build_payload(profile: dict, prompt: str, context: list[dict], stream: bool = False):
    provider = str(profile.get("provider") or "").strip().lower()
    base_url = str(profile.get("base_url") or "").strip().lower()
    model = profile.get("model")

    if provider == "ollama" or base_url.endswith("/api/chat"):
        messages = list(context or [])
        messages.append({"role": "user", "content": prompt})
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

    payload = {"prompt": prompt}
    if model not in (None, ""):
        payload["model"] = model
    if context:
        payload["context"] = context
    if stream:
        payload["stream"] = True
    return payload


def _decode_response(resp):
    raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    ctype = (resp.headers.get("Content-Type") or "").lower()

    if "application/json" in ctype:
        try:
            return json.loads(text)
        except Exception as exc:
            raise QCallError(f"invalid JSON response: {exc}") from exc

    try:
        return json.loads(text)
    except Exception:
        return text


def call_profile(profile: dict, prompt: str, context: list[dict] | None = None):
    endpoint = profile.get("base_url")
    timeout = profile.get("timeout_seconds")
    headers = build_headers(profile)

    if not endpoint:
        raise QCallError("q profile base_url missing")
    if timeout is None:
        raise QCallError("q profile timeout_seconds missing")

    payload = _build_payload(profile, prompt, list(context or []), stream=False)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            return _decode_response(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise QCallError(f"q endpoint HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise QCallError(f"q endpoint error: {exc.reason}") from exc


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


def extract_raw_value(payload, chat_message_tag: str | list[str] | None):
    if isinstance(payload, str):
        return payload

    if isinstance(payload, (dict, list)):
        for path in _normalize_path_list(chat_message_tag):
            value = deep_get(payload, path)
            if value is not None:
                return value

        for fallback in _FALLBACK_PATHS:
            value = deep_get(payload, fallback)
            if value is not None:
                return value

        return payload

    raise QCallError(f"unsupported q response type: {type(payload).__name__}")


def extract_stream_chunk(
    payload,
    stream_message_tag: str | list[str] | None,
    chat_message_tag: str | list[str] | None,
) -> str:
    if isinstance(payload, str):
        return payload

    if not isinstance(payload, dict):
        return ""

    paths: list[str] = []
    paths.extend(_normalize_path_list(stream_message_tag))
    paths.extend(_normalize_path_list(chat_message_tag))

    for fallback in _STREAM_FALLBACK_PATHS:
        if fallback not in paths:
            paths.append(fallback)

    return _extract_first_nonempty_scalar(payload, paths)


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

    if isinstance(parsed, _ALLOWED_QC_TYPES):
        return parsed

    return value


def decode_qc_output(payload, chat_message_tag: str | list[str] | None):
    value = extract_raw_value(payload, chat_message_tag)

    if isinstance(value, str):
        value = _maybe_parse_json_string(value)

    if not isinstance(value, _ALLOWED_QC_TYPES):
        raise QCallError("qc accepts only string, list or dict")

    return value


def profile_has_stream(profile: dict) -> bool:
    return len(_normalize_path_list(profile.get("stream_message_tag"))) > 0


def stream_profile(profile: dict, prompt: str, context: list[dict] | None = None) -> Iterable[str]:
    endpoint = profile.get("base_url")
    timeout = profile.get("timeout_seconds")
    headers = build_headers(profile)

    if not endpoint:
        raise QCallError("q profile base_url missing")
    if timeout is None:
        raise QCallError("q profile timeout_seconds missing")

    payload = _build_payload(profile, prompt, list(context or []), stream=True)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()

            if "text/event-stream" in ctype:
                events = _iter_sse_events(resp)
            else:
                events = _iter_jsonl_events(resp)

            stream_message_tag = profile.get("stream_message_tag")
            chat_message_tag = profile.get("chat_message_tag")

            for event in events:
                chunk = extract_stream_chunk(
                    event,
                    stream_message_tag=stream_message_tag,
                    chat_message_tag=chat_message_tag,
                )
                if chunk:
                    yield chunk

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise QCallError(f"q endpoint HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise QCallError(f"q endpoint error: {exc.reason}") from exc


def prepare_q_session(parser, command_token: str, prompt: str) -> dict:
    profile_name = resolve_profile_name(parser, command_token, "q")
    profile = get_profile(parser, profile_name)
    set_active_profile(parser, profile_name)

    chat_symbol = chat_symbol_for_profile(profile_name)
    system_prompt = get_system_prompt(parser, profile_name)

    chat = load_chat(parser.state, chat_symbol)
    context = chat_to_messages(chat, system_prompt=system_prompt)
    expanded_prompt = expand_prompt_tokens(parser, prompt.split())

    return {
        "profile_name": profile_name,
        "profile": profile,
        "chat_symbol": chat_symbol,
        "prompt": prompt,
        "expanded_prompt": expanded_prompt,
        "context": context,
        "stream_enabled": 1 if profile_has_stream(profile) else 0,
    }


def run_nonstream_session(session: dict) -> str:
    payload = call_profile(
        session["profile"],
        session["expanded_prompt"],
        session["context"],
    )
    return extract_chat(payload, session["profile"].get("chat_message_tag"))


def q_chat(
    parser,
    command_token: str,
    prompt: str,
    on_chunk: Callable[[str, str, str, str], None] | None = None,
    on_done: Callable[[str, str, str], None] | None = None,
) -> dict:
    session = prepare_q_session(parser, command_token, prompt)
    profile_name = session["profile_name"]
    chat_symbol = session["chat_symbol"]

    if not session["stream_enabled"]:
        out = write_full_chat_entry(
            parser.state,
            chat_symbol,
            prompt,
            run_nonstream_session(session),
        )
        final_text = out["message"]
        if callable(on_done):
            on_done(final_text, chat_symbol, out["chat_key"])

        return {
            "profile": profile_name,
            "chat_symbol": chat_symbol,
            "chat_key": out["chat_key"],
            "message": final_text,
        }

    key = open_chat_entry(parser.state, chat_symbol, prompt)
    final_text = ""

    try:
        for chunk in stream_profile(
            session["profile"],
            session["expanded_prompt"],
            session["context"],
        ):
            final_text = append_chat_chunk(parser.state, chat_symbol, key, chunk)
            if callable(on_chunk):
                on_chunk(chunk, final_text, chat_symbol, key)
    finally:
        item = close_chat_entry(parser.state, chat_symbol, key)
        final_text = str(item.get("response") or "")
        if callable(on_done):
            on_done(final_text, chat_symbol, key)

    return {
        "profile": profile_name,
        "chat_symbol": chat_symbol,
        "chat_key": key,
        "message": final_text,
    }


def qc_raw(parser, command_token: str, prompt: str) -> dict:
    profile_name = resolve_profile_name(parser, command_token, "qc")
    profile = get_profile(parser, profile_name)

    expanded_prompt = expand_prompt_tokens(parser, prompt.split())
    payload = call_profile(profile, expanded_prompt, [])
    decoded = decode_qc_output(payload, profile.get("chat_message_tag"))

    return {
        "profile": profile_name,
        "decoded": decoded,
        "raw": payload,
    }


def health_q_profile(parser, profile_name: str) -> str:
    profile = get_profile(parser, profile_name)
    health_url = str(profile.get("health_url") or "").strip()
    label = "q" if profile_name == "default" else f"q.{profile_name}"

    if not health_url:
        return f"[fail] {label} missing health_url"

    headers = build_headers(profile)
    timeout = float(profile.get("timeout_seconds") or 5)
    req = urllib.request.Request(health_url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return f"[ok] {label}"
            return f"[fail] {label} HTTP {resp.status}"
    except Exception as exc:
        return f"[fail] {label} {exc}"
