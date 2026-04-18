from __future__ import annotations

from typing import Any

from .common import read_state_value

_ROLE_PROFILE_KEYS = (
    'temperature',
    'top_k',
    'top_p',
    'repeat_penalty',
    'max_tokens',
    'seed',
    'num_ctx',
    'think',
    'thinking',
    'stream',
)


def normalize_role_name(value: Any) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    if raw.startswith('#ROLES:'):
        raw = raw[len('#ROLES:'):].strip()
        raw = raw[:-5] if raw.endswith('.role') else raw
        return raw.replace(':', '/')
    raw = raw.strip('/').replace('\\', '/').replace(':', '/')
    if raw.endswith('.role'):
        raw = raw[:-5]
    if raw.endswith('.system'):
        raw = raw[:-7]
    return raw.strip('/')


def role_symbol_from_name(value: Any, suffix: str = '.role') -> str:
    name = normalize_role_name(value)
    if not name:
        return ''
    body = name.replace('/', ':')
    if suffix and not suffix.startswith('.'):
        suffix = '.' + suffix
    return f'#ROLES:{body}{suffix or ""}'


def read_role_preset(state, value: Any) -> dict[str, Any]:
    symbol = role_symbol_from_name(value, '.role')
    if not symbol:
        return {}
    payload = read_state_value(state, symbol, None)
    return dict(payload) if isinstance(payload, dict) else {}


def read_role_system_prompt(state, value: Any) -> str:
    symbol = role_symbol_from_name(value, '.system')
    if not symbol:
        return ''
    return str(read_state_value(state, symbol, '') or '')


def resolve_role_value(state, value: Any) -> dict[str, Any]:
    role_name = normalize_role_name(value)
    if not role_name:
        return {
            'kind': 'empty',
            'role': '',
            'system_prompt': '',
            'profile_overrides': {},
            'preset': {},
        }
    preset = read_role_preset(state, role_name)
    system_prompt = read_role_system_prompt(state, role_name)
    if preset or system_prompt:
        profile_overrides = {
            key: preset[key]
            for key in _ROLE_PROFILE_KEYS
            if key in preset and preset.get(key) not in (None, '')
        }
        return {
            'kind': 'preset',
            'role': role_name,
            'system_prompt': system_prompt,
            'profile_overrides': profile_overrides,
            'preset': preset,
        }
    return {
        'kind': 'missing',
        'role': role_name,
        'system_prompt': '',
        'profile_overrides': {},
        'preset': {},
    }


__all__ = [
    'normalize_role_name',
    'role_symbol_from_name',
    'read_role_preset',
    'read_role_system_prompt',
    'resolve_role_value',
]
