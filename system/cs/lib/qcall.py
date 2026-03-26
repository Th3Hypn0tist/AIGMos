# system/cs/lib/qcall.py

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request

from system.cs.lib.state_tree import resolve_exact_or_branch


_SYMBOL_ROOTS = "$#&%@!"
_ALLOWED_QC_TYPES = (str, list, dict)
_FALLBACK_PATHS = (
    "message.content",
    "message",
    "text",
    "response",
    "choices.0.message.content",
)


class QCallError(RuntimeError):
    pass


class QHealthError(RuntimeError):
    pass


def is_target_token(token: str) -> bool:
    return bool(token) and token[0] in _SYMBOL_ROOTS


def deep_get(obj, path: str):
    cur = obj

    for part in path.split("."):
        if isinstance(cur, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(cur):
                return None
            cur = cur[idx]
            continue

        if isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
            continue

        return None

    return cur


def to_plain_string(value) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        raise QCallError("empty q response")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def get_root_config(parser):
    runtime = getattr(parser, "runtime", None)
    if isinstance(runtime, dict):
        cfg = runtime.get("config")
        if isinstance(cfg, dict):
            return cfg

    cfg = getattr(parser, "config", None)
    if isinstance(cfg, dict):
        return cfg

    return None


def get_profile(parser, profile_name: str) -> dict:
    cfg = get_root_config(parser)
    if not isinstance(cfg, dict):
        raise QCallError("missing config root")

    qcfg = cfg.get("q")
    if not isinstance(qcfg, dict):
        raise QCallError("missing q config")

    profile = qcfg.get(profile_name)
    if not isinstance(profile, dict):
        raise QCallError(f"missing q profile: {profile_name}")

    return profile


def build_headers(profile: dict) -> dict:
    headers = dict(profile.get("headers") or {})

    if not any(k.lower() == "content-type" for k in headers):
        headers["Content-Type"] = "application/json"

    api_key = profile.get("api_key")
    has_auth = any(k.lower() == "authorization" for k in headers)

    if api_key and not has_auth:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


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


def set_active_profile(parser, profile_name: str) -> None:
    get_profile(parser, profile_name)
    parser.runtime["q_profile"] = profile_name
    parser.runtime["q_chat_symbol"] = chat_symbol_for_profile(profile_name)


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


def _empty_chat() -> dict:
    return {"turns": []}


def load_chat(state, symbol: str) -> dict:
    out = state.get(symbol)
    if out["error"]:
        raise QCallError(out["error"])

    current = out["result"]
    if not isinstance(current, dict):
        return _empty_chat()

    turns = current.get("turns")
    if not isinstance(turns, list):
        return _empty_chat()

    return {"turns": list(turns)}


def append_turn(state, symbol: str, q_text: str, a_text: str, profile_name: str) -> None:
    chat = load_chat(state, symbol)
    turns = list(chat.get("turns") or [])
    turns.append(
        {
            "q": {"text": q_text},
            "a": {"text": a_text},
            "profile": profile_name,
        }
    )

    out = state.set(symbol, {"turns": turns})
    if out["error"]:
        raise QCallError(out["error"])


def chat_to_messages(chat: dict) -> list[dict]:
    messages = []

    for turn in chat.get("turns") or []:
        if not isinstance(turn, dict):
            continue

        q_text = deep_get(turn, "q.text")
        if isinstance(q_text, str) and q_text:
            messages.append({"role": "user", "content": q_text})

        a_text = deep_get(turn, "a.text")
        if isinstance(a_text, str) and a_text:
            messages.append({"role": "assistant", "content": a_text})

    return messages


def expand_prompt_tokens(parser, tokens: list[str]) -> str:
    expanded = []

    for token in tokens:
        if is_target_token(token):
            value = _resolve_q_token(parser, token)

            if isinstance(value, (dict, list)):
                expanded.append(json.dumps(value, ensure_ascii=False))
            elif value is None:
                expanded.append("null")
            else:
                expanded.append(str(value))
            continue

        expanded.append(token)

    return " ".join(expanded).strip()


def _resolve_q_token(parser, token: str):
    try:
        return resolve_exact_or_branch(parser, token)
    except RuntimeError as exc:
        raise QCallError(str(exc)) from exc


def _build_payload(profile: dict, prompt: str, context: list[dict]):
    provider = str(profile.get("provider") or "").strip().lower()
    base_url = str(profile.get("base_url") or "").strip().lower()
    model = profile.get("model")

    if provider == "ollama" or base_url.endswith("/api/chat"):
        messages = list(context or [])
        messages.append({"role": "user", "content": prompt})
        return {
            "model": model,
            "messages": messages,
            "stream": False,
        }

    payload = {"prompt": prompt}
    if model not in (None, ""):
        payload["model"] = model
    if context:
        payload["context"] = context
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

    payload = _build_payload(profile, prompt, list(context or []))
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
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            raise QCallError("q endpoint timeout") from exc
        raise QCallError(f"q endpoint error: {reason}") from exc

    except socket.timeout as exc:
        raise QCallError("q endpoint timeout") from exc

    except TimeoutError as exc:
        raise QCallError("q endpoint timeout") from exc

    except ConnectionRefusedError as exc:
        raise QCallError("q endpoint connection refused") from exc

    except OSError as exc:
        raise QCallError(f"q endpoint error: {exc}") from exc


def extract_raw_value(payload, chat_message_tag: str | None):
    if isinstance(payload, str):
        return payload

    if isinstance(payload, (dict, list)):
        if chat_message_tag:
            value = deep_get(payload, chat_message_tag)
            if value is not None:
                return value

        for fallback in _FALLBACK_PATHS:
            value = deep_get(payload, fallback)
            if value is not None:
                return value

        return payload

    raise QCallError(f"unsupported q response type: {type(payload).__name__}")


def extract_chat(payload, chat_message_tag: str | None) -> str:
    return to_plain_string(extract_raw_value(payload, chat_message_tag))


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


def decode_qc_output(payload, chat_message_tag: str | None):
    value = extract_raw_value(payload, chat_message_tag)

    if isinstance(value, str):
        value = _maybe_parse_json_string(value)

    if not isinstance(value, _ALLOWED_QC_TYPES):
        raise QCallError("qc accepts only string, list or dict")

    return value


def q_chat(parser, command_token: str, prompt: str) -> dict:
    profile_name = resolve_profile_name(parser, command_token, "q")
    profile = get_profile(parser, profile_name)
    chat_symbol = chat_symbol_for_profile(profile_name)
    chat = load_chat(parser.state, chat_symbol)

    expanded_prompt = expand_prompt_tokens(parser, prompt.split())
    payload = call_profile(profile, expanded_prompt, chat_to_messages(chat))
    message = extract_chat(payload, profile.get("chat_message_tag"))

    append_turn(parser.state, chat_symbol, expanded_prompt, message, profile_name)
    return {
        "profile": profile_name,
        "chat_symbol": chat_symbol,
        "message": message,
        "raw": payload,
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

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            status = getattr(resp, "status", 200)
            return f"[ok] {label} {status} in {elapsed_ms} ms"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return f"[fail] {label} HTTP {exc.code}: {body or exc.reason}"
    except urllib.error.URLError as exc:
        return f"[fail] {label} {exc.reason}"
