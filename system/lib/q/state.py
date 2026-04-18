from __future__ import annotations

from typing import Any

from system.state.api import write_value

from .common import profile_name_from_q_symbol, q_writer, read_state_value
from .errors import QCallError
from .symbols import role_symbol_for_profile


def _next_chat_key(chat: dict) -> str:
    max_num = 0
    for key in chat.keys():
        try:
            max_num = max(max_num, int(str(key)))
        except Exception:
            continue
    return str(max_num + 1)


def load_chat(state, symbol: str) -> dict:
    current = read_state_value(state, symbol, {})
    if not isinstance(current, dict):
        return {}
    clean: dict[str, dict] = {}
    for key, value in current.items():
        if not isinstance(value, dict):
            continue
        clean[str(key)] = {
            "prompt": str(value.get("prompt") or ""),
            "response": str(value.get("response") or ""),
            "done": 1 if int(value.get("done") or 0) else 0,
        }
    return clean


def save_chat(state, symbol: str, chat: dict) -> None:
    out = write_value(state, symbol, chat, writer=q_writer(profile_name_from_q_symbol(symbol)), op="chat_save")
    if out["error"]:
        raise QCallError(out["error"])


def _ensure_chat_node(chat: dict, key: str, *, prompt: str | None = None, response: str | None = None, done: int | None = None) -> dict:
    node_key = str(key)
    item = chat.get(node_key)
    if not isinstance(item, dict):
        item = {"prompt": "", "response": "", "done": 0}
    else:
        item = {
            "prompt": str(item.get("prompt") or ""),
            "response": str(item.get("response") or ""),
            "done": 1 if int(item.get("done") or 0) else 0,
        }
    if prompt is not None:
        item["prompt"] = str(prompt or "")
    if response is not None:
        item["response"] = str(response or "")
    if done is not None:
        item["done"] = 1 if int(done or 0) else 0
    chat[node_key] = item
    return item


def load_role(state, symbol: str) -> str:
    value = read_state_value(state, symbol, "")
    return str(value or "")


def get_system_prompt(parser, profile_name: str) -> str:
    from .symbols import system_prompt_symbol_for_profile
    return load_role(parser.state, system_prompt_symbol_for_profile(profile_name))


def write_text_symbol(state, symbol: str, value: str, op: str) -> None:
    out = write_value(state, symbol, str(value or ""), writer=q_writer(profile_name_from_q_symbol(symbol)), op=op)
    if out["error"]:
        raise QCallError(out["error"])


def open_chat_entry(state, symbol: str, prompt: str) -> str:
    chat = load_chat(state, symbol)
    key = _next_chat_key(chat)
    _ensure_chat_node(chat, key, prompt=prompt, response="", done=0)
    save_chat(state, symbol, chat)
    return key


def append_response_stream(current: str, incoming: str) -> str:
    cur = str(current or "")
    inc = str(incoming or "")
    if not inc:
        return cur
    return cur + inc


def merge_thinking_stream(current: str, incoming: str) -> str:
    cur = str(current or "")
    inc = str(incoming or "")
    if not inc:
        return cur
    if not cur:
        return inc
    if inc == cur:
        return cur
    if len(inc) > len(cur) and inc.startswith(cur):
        return inc
    return cur + inc


def append_chat_chunk(state, symbol: str, key: str, chunk: str) -> str:
    chat = load_chat(state, symbol)
    item = chat.get(str(key))
    if not isinstance(item, dict):
        raise QCallError(f"chat entry missing: {symbol}:{key}")
    current_response = str(item.get("response") or "")
    merged_response = append_response_stream(current_response, str(chunk or ""))
    _ensure_chat_node(chat, key, response=merged_response, done=0)
    save_chat(state, symbol, chat)
    return merged_response


def write_chat_entry(state, symbol: str, key: str, prompt: str, response: str, *, done: int) -> dict:
    chat = load_chat(state, symbol)
    item = _ensure_chat_node(chat, key, prompt=str(prompt or ""), response=str(response or ""), done=done)
    save_chat(state, symbol, chat)
    return dict(item)


def close_chat_entry(state, symbol: str, key: str, final_response: str | None = None) -> dict:
    chat = load_chat(state, symbol)
    item = chat.get(str(key))
    if not isinstance(item, dict):
        raise QCallError(f"chat entry missing: {symbol}:{key}")
    prompt = str(item.get("prompt") or "")
    response = str(item.get("response") or "")
    if final_response is not None:
        response = str(final_response)
    item = _ensure_chat_node(chat, key, prompt=prompt, response=response, done=1)
    save_chat(state, symbol, chat)
    return dict(item)


def write_full_chat_entry(state, symbol: str, prompt: str, response: str) -> dict:
    chat = load_chat(state, symbol)
    key = _next_chat_key(chat)
    item = _ensure_chat_node(chat, key, prompt=prompt, response=str(response or ""), done=1)
    save_chat(state, symbol, chat)
    return {"chat_key": key, "item": dict(item), "message": str(item.get("response") or "")}


__all__ = [
    "append_chat_chunk",
    "close_chat_entry",
    "get_system_prompt",
    "load_chat",
    "load_role",
    "open_chat_entry",
    "save_chat",
    "write_chat_entry",
    "write_full_chat_entry",
    "append_response_stream",
    "merge_thinking_stream",
    "write_text_symbol",
]
