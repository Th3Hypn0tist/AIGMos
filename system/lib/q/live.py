from __future__ import annotations

from typing import Any

from system.cs.live_packet import get_live_packet as get_named_live_packet
from system.cs.live_session import chunk_live_session, done_live_session, fail_live_session, open_live_session, read_live_session

from .common import read_state_value
from .state import load_chat
from .symbols import get_active_chat_symbol, get_active_thinking_symbol


_Q_LIVE_DEFAULTS = {
    'profile': 'default',
    'chat_symbol': '',
    'response_symbol': '',
    'thinking_symbol': '',
    'key': '',
    'prompt': '',
    'response': '',
    'thinking': '',
    'done': 1,
}


def _q_live_name(chat_symbol: str | None) -> str:
    clean = str(chat_symbol or '').strip()
    return f"q.session:{clean}" if clean else 'q.session'


def _q_runtime(parser, chat_symbol: str | None = None) -> dict:
    return read_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS)


def _q_live_fields(*, profile: str | None = None, chat_symbol: str | None = None, response_symbol: str | None = None, thinking_symbol: str | None = None, key: str | None = None, prompt: str | None = None, response: str | None = None, thinking: str | None = None) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if profile is not None:
        fields['profile'] = str(profile or 'default')
    if chat_symbol is not None:
        fields['chat_symbol'] = str(chat_symbol or '')
    if response_symbol is not None:
        fields['response_symbol'] = str(response_symbol or '')
    if thinking_symbol is not None:
        fields['thinking_symbol'] = str(thinking_symbol or '')
    if key is not None:
        fields['key'] = str(key or '')
    if prompt is not None:
        fields['prompt'] = str(prompt or '')
    if response is not None:
        fields['response'] = str(response or '')
    if thinking is not None:
        fields['thinking'] = str(thinking or '')
    return fields


def open_q_live(parser, **kwargs: Any) -> dict[str, Any]:
    chat_symbol = kwargs.get('chat_symbol')
    return open_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS, **_q_live_fields(**kwargs))


def chunk_q_live(parser, **kwargs: Any) -> dict[str, Any]:
    chat_symbol = kwargs.get('chat_symbol')
    return chunk_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS, **_q_live_fields(**kwargs))


def done_q_live(parser, **kwargs: Any) -> dict[str, Any]:
    chat_symbol = kwargs.get('chat_symbol')
    return done_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS, **_q_live_fields(**kwargs))


def fail_q_live(parser, error: Any, **kwargs: Any) -> dict[str, Any]:
    chat_symbol = kwargs.get('chat_symbol')
    return fail_live_session(parser, _q_live_name(chat_symbol), error, defaults=_Q_LIVE_DEFAULTS, **_q_live_fields(**kwargs))


def get_live_chat(parser, chat_symbol: str | None = None) -> dict:
    symbol = str(chat_symbol or '').strip()
    if not symbol:
        symbol = get_active_chat_symbol(parser)
    if not symbol:
        return {}
    try:
        chat = load_chat(parser.state, symbol)
    except Exception:
        chat = {}
    live = _q_runtime(parser, symbol)
    if str(live.get('chat_symbol') or '') != symbol:
        return chat
    key = str(live.get('key') or '')
    if not key:
        return chat
    item = chat.get(key)
    if not isinstance(item, dict):
        item = {'prompt': str(live.get('prompt') or ''), 'response': '', 'done': 0}
    item = dict(item)
    item['prompt'] = str(live.get('prompt') or item.get('prompt') or '')
    item['response'] = str(live.get('response') or item.get('response') or '')
    item['done'] = int(live.get('done') or 0)
    chat = dict(chat)
    chat[key] = item
    return chat


def get_live_thinking(parser, thinking_symbol: str | None = None) -> str:
    symbol = str(thinking_symbol or '').strip()
    if not symbol:
        symbol = get_active_thinking_symbol(parser)
    live = _q_runtime(parser, None)
    live_symbol = str(live.get('thinking_symbol') or '')
    if symbol and live_symbol == symbol:
        return str(live.get('thinking') or '')
    value = read_state_value(parser.state, symbol, '')
    return str(value or '')


def get_live_packet(parser, chat_symbol: str | None = None) -> dict[str, Any]:
    if chat_symbol:
        return read_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS)
    return get_named_live_packet(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS)


def shutdown_live_chat(parser, timeout: float = 1.5, chat_symbol: str | None = None) -> None:
    try:
        done_live_session(parser, _q_live_name(chat_symbol), defaults=_Q_LIVE_DEFAULTS, done=1)
    except Exception:
        pass


__all__ = [
    '_Q_LIVE_DEFAULTS',
    'open_q_live',
    'chunk_q_live',
    'done_q_live',
    'fail_q_live',
    'get_live_chat',
    'get_live_packet',
    'get_live_thinking',
    'shutdown_live_chat',
]
