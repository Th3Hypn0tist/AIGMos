from __future__ import annotations

from typing import Any

from system.lib.trigger.types import TriggerState


def coerce_pulse_ms(value: Any) -> int:
    raw = str(value if value is not None else '').strip()
    if raw == '':
        raise ValueError('pulse must be a non-negative integer')
    try:
        number = int(raw)
    except Exception as exc:
        raise ValueError('pulse must be a non-negative integer') from exc
    if number < 0:
        raise ValueError('pulse must be a non-negative integer')
    return number


def can_fire(now_ms: int, last_fire_ms: int, pulse_ms: int) -> bool:
    now = int(now_ms)
    last = int(last_fire_ms)
    pulse = int(pulse_ms)
    if pulse <= 0:
        return True
    return (now - last) >= pulse


def mark_fired(state: TriggerState, now_ms: int) -> TriggerState:
    state.last_fire_ms = int(now_ms)
    return state
