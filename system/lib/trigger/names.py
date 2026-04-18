from __future__ import annotations

import re
from typing import Tuple

from system.lib.trigger.types import ALLOWED_TRIGGER_FIELDS

_SEGMENT_RE = re.compile(r'^[A-Za-z0-9._]+$')


def _validate_segment(segment: str, *, role: str) -> str:
    text = str(segment or '').strip()
    if not text:
        raise ValueError(f'{role} segment cannot be empty')
    if text.startswith('.'):
        raise ValueError(f'{role} segment cannot start with .')
    if text.endswith('.'):
        raise ValueError(f'{role} segment cannot end with .')
    if not _SEGMENT_RE.fullmatch(text):
        raise ValueError(f'invalid {role} segment: {text}')
    return text


def _validate_body(text: str, *, role: str) -> str:
    raw = str(text or '').strip()
    if not raw:
        raise ValueError(f'{role} cannot be empty')
    if raw.endswith(':') or '::' in raw:
        raise ValueError(f'invalid {role}: {raw}')

    parts = raw.split(':')
    for part in parts:
        _validate_segment(part, role=role)
    return ':'.join(parts)


def validate_trigger_name(name: str) -> str:
    raw = str(name or '').strip()
    if raw.startswith('!'):
        raw = raw[1:]
    elif raw.startswith('@'):
        raise ValueError('trigger name must not start with @')

    clean = _validate_body(raw, role='trigger name')
    last = clean.rsplit(':', 1)[-1]
    if last in ALLOWED_TRIGGER_FIELDS:
        raise ValueError(f'trigger name must not end with reserved field: {last}')
    return clean


def validate_event_name(name: str) -> str:
    raw = str(name or '').strip()
    if raw.startswith('@'):
        raw = raw[1:]
    elif raw.startswith('!'):
        raise ValueError('event name must not start with !')
    return _validate_body(raw, role='event name')


def split_runtime_field(path: str) -> Tuple[str, str, str]:
    raw = str(path or '').strip()
    if not raw:
        raise ValueError('runtime path cannot be empty')

    prefix = raw[0]
    if prefix not in {'!', '@'}:
        raise ValueError(f'runtime path must start with ! or @: {raw}')

    body = raw[1:]
    if not body:
        raise ValueError(f'runtime path cannot be bare root: {raw}')

    if prefix == '!':
        candidate = _validate_body(body, role='trigger path')
        if ':' not in candidate:
            raise ValueError(f'trigger field path must end with :state or :pulse: {raw}')
        name, field = candidate.rsplit(':', 1)
        if field not in ALLOWED_TRIGGER_FIELDS:
            raise ValueError(f'invalid trigger field: {field}')
        validate_trigger_name(name)
        return prefix, name, field

    clean = validate_event_name(body)
    return prefix, clean, ''


def validate_trigger_field_path(path: str) -> tuple[str, str]:
    prefix, name, field = split_runtime_field(path)
    if prefix != '!':
        raise ValueError(f'trigger field path must start with !: {path}')
    return name, field


def validate_event_path(path: str) -> str:
    raw = str(path or '').strip()
    if not raw.startswith('@'):
        raise ValueError(f'event path must start with @: {path}')
    prefix, name, field = split_runtime_field(raw)
    if prefix != '@' or field:
        raise ValueError(f'invalid event path: {path}')
    return name
