from __future__ import annotations

from datetime import datetime, timezone

from system.lib.trigger.cron_spec import normalize_cron_spec
from system.lib.trigger.types import TriggerState


def is_cron_due(spec: str, now_dt: datetime, state: TriggerState) -> bool:
    normalized = normalize_cron_spec(spec)
    tick = _tick_key(normalized, now_dt)
    if not _matches(normalized, now_dt):
        return False
    return str(state.last_cron_tick or '') != tick


def mark_cron_fired(state: TriggerState, spec: str, now_dt: datetime) -> TriggerState:
    normalized = normalize_cron_spec(spec)
    state.last_cron_tick = _tick_key(normalized, now_dt)
    return state


def _matches(spec: str, now_dt: datetime) -> bool:
    if spec.startswith('every '):
        return True

    minute, hour, dom, month, dow = spec.split()
    current_dow = (now_dt.weekday() + 1) % 7
    return all(
        (
            _field_matches(minute, now_dt.minute),
            _field_matches(hour, now_dt.hour),
            _field_matches(dom, now_dt.day),
            _field_matches(month, now_dt.month),
            _field_matches(dow, current_dow, allow_seven_as_sunday=True),
        )
    )


def _tick_key(spec: str, now_dt: datetime) -> str:
    if spec.startswith('every '):
        count_text, unit = spec.split()[1][:-1], spec.split()[1][-1]
        count = int(count_text)
        if unit == 's':
            epoch = int(now_dt.replace(tzinfo=timezone.utc).timestamp())
            return f's:{epoch // count}'
        if unit == 'm':
            serial = (((now_dt.year * 12 + now_dt.month) * 31 + now_dt.day) * 24 + now_dt.hour) * 60 + now_dt.minute
            return f'm:{serial // count}'
        if unit == 'h':
            serial = (((now_dt.year * 12 + now_dt.month) * 31 + now_dt.day) * 24 + now_dt.hour)
            return f'h:{serial // count}'
        if unit == 'd':
            return f'd:{now_dt.toordinal() // count}'
        raise ValueError(f'unsupported cron unit: {unit}')
    return now_dt.strftime('cron:%Y-%m-%dT%H:%M')


def _field_matches(field: str, value: int, *, allow_seven_as_sunday: bool = False) -> bool:
    for part in field.split(','):
        if _part_matches(part.strip(), value, allow_seven_as_sunday=allow_seven_as_sunday):
            return True
    return False


def _part_matches(part: str, value: int, *, allow_seven_as_sunday: bool = False) -> bool:
    base = part
    step = 1
    if '/' in part:
        base, step_text = part.split('/', 1)
        step = int(step_text)

    if base == '*':
        return (value % step) == 0 if step > 1 else True

    if '-' in base:
        left_text, right_text = base.split('-', 1)
        left = int(left_text)
        right = int(right_text)
        check_value = 0 if allow_seven_as_sunday and value == 0 else value
        if allow_seven_as_sunday and right == 7 and check_value == 0:
            check_value = 7
        if check_value < left or check_value > right:
            return False
        return ((check_value - left) % step) == 0

    target = int(base)
    check_value = value
    if allow_seven_as_sunday and target == 7 and value == 0:
        check_value = 7
    return check_value == target
