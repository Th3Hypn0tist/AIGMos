from __future__ import annotations

import re

_CRON_RE = re.compile(r'^\S+(?:\s+\S+){4}$')
_EVERY_RE = re.compile(
    r'^every\s+(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$',
    re.IGNORECASE,
)

_SHORTHANDS = {
    'daily': '0 0 * * *',
    'hourly': '0 * * * *',
    'minutely': '* * * * *',
}


def is_shorthand(spec: str) -> bool:
    raw = str(spec or '').strip().lower()
    return raw in _SHORTHANDS or bool(_EVERY_RE.fullmatch(raw))


def expand_shorthand(spec: str) -> str:
    raw = str(spec or '').strip().lower()
    if raw in _SHORTHANDS:
        return _SHORTHANDS[raw]

    match = _EVERY_RE.fullmatch(raw)
    if not match:
        raise ValueError(f'invalid cron shorthand: {spec}')

    count = int(match.group(1))
    unit = _normalize_unit(match.group(2))
    return f'every {count}{unit}'


def normalize_cron_spec(spec: str) -> str:
    raw = ' '.join(str(spec or '').strip().split())
    if not raw:
        raise ValueError('cron spec cannot be empty')

    lower = raw.lower()
    if is_shorthand(lower):
        return expand_shorthand(lower)

    validate_cron_spec(raw)
    return raw


def validate_cron_spec(spec: str) -> str:
    raw = ' '.join(str(spec or '').strip().split())
    if not raw:
        raise ValueError('cron spec cannot be empty')

    lower = raw.lower()
    if is_shorthand(lower):
        return expand_shorthand(lower)

    if not _CRON_RE.fullmatch(raw):
        raise ValueError(f'invalid cron spec: {spec}')

    fields = raw.split()
    if len(fields) != 5:
        raise ValueError(f'invalid cron spec: {spec}')

    mins, hours, dom, month, dow = fields
    _validate_field(mins, 0, 59, role='minute')
    _validate_field(hours, 0, 23, role='hour')
    _validate_field(dom, 1, 31, role='day-of-month')
    _validate_field(month, 1, 12, role='month')
    _validate_field(dow, 0, 7, role='day-of-week')
    return raw


def _validate_field(field: str, minimum: int, maximum: int, *, role: str) -> None:
    for part in str(field or '').split(','):
        part = part.strip()
        if not part:
            raise ValueError(f'invalid {role} field')
        _validate_part(part, minimum, maximum, role=role)


def _validate_part(part: str, minimum: int, maximum: int, *, role: str) -> None:
    base = part
    step_text = ''
    if '/' in part:
        base, step_text = part.split('/', 1)
        if not step_text.isdigit() or int(step_text) <= 0:
            raise ValueError(f'invalid {role} step: {part}')

    if base == '*':
        return

    if '-' in base:
        left, right = base.split('-', 1)
        _validate_int(left, minimum, maximum, role=role)
        _validate_int(right, minimum, maximum, role=role)
        if int(left) > int(right):
            raise ValueError(f'invalid {role} range: {part}')
        return

    _validate_int(base, minimum, maximum, role=role)


def _validate_int(text: str, minimum: int, maximum: int, *, role: str) -> None:
    if not str(text or '').isdigit():
        raise ValueError(f'invalid {role} value: {text}')
    value = int(text)
    if value < minimum or value > maximum:
        raise ValueError(f'invalid {role} value: {text}')


def _normalize_unit(unit: str) -> str:
    raw = str(unit or '').strip().lower()
    if raw in {'s', 'sec', 'secs', 'second', 'seconds'}:
        return 's'
    if raw in {'m', 'min', 'mins', 'minute', 'minutes'}:
        return 'm'
    if raw in {'h', 'hr', 'hrs', 'hour', 'hours'}:
        return 'h'
    if raw in {'d', 'day', 'days'}:
        return 'd'
    raise ValueError(f'invalid cron unit: {unit}')
