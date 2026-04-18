from __future__ import annotations

from typing import Any

from system.lib.trigger.names import (
    validate_event_name,
    validate_event_path,
    validate_trigger_field_path,
    validate_trigger_name,
)
from system.lib.trigger.store import (
    delete_event_def,
    delete_trigger_def,
    delete_trigger_state,
    load_event_def,
    load_trigger_def,
    load_trigger_state,
    save_event_def,
    save_trigger_def,
    save_trigger_state,
)
from system.lib.trigger.types import EventDef, TriggerDef, TriggerState


def create_trigger(ctx_or_parser, trigger_def: TriggerDef) -> TriggerDef:
    clean_name = validate_trigger_name(trigger_def.name)
    if load_trigger_def(ctx_or_parser, clean_name) is not None:
        raise ValueError('name exists')

    normalized = TriggerDef(
        name=clean_name,
        kind=str(trigger_def.kind or '').strip(),
        expr=str(trigger_def.expr or ''),
        source=str(trigger_def.source or ''),
        cron_spec=str(trigger_def.cron_spec or ''),
        pulse_ms=_coerce_pulse_ms(trigger_def.pulse_ms),
    )
    save_trigger_def(ctx_or_parser, normalized)
    save_trigger_state(
        ctx_or_parser,
        clean_name,
        TriggerState(state='0', pulse_ms=normalized.pulse_ms),
    )
    return normalized


def remove_trigger(ctx_or_parser, name: str) -> bool:
    clean_name = validate_trigger_name(name)
    existed = load_trigger_def(ctx_or_parser, clean_name) is not None
    state_snapshot = load_trigger_state(ctx_or_parser, clean_name)
    has_runtime = (
        state_snapshot.state in {'0', '1'}
        or state_snapshot.pulse_ms != 0
        or bool(state_snapshot.last_value)
        or bool(state_snapshot.baseline_value)
        or bool(state_snapshot.last_cron_tick)
        or state_snapshot.last_fire_ms != 0
    )

    if not existed and not has_runtime:
        return False

    if existed:
        delete_trigger_def(ctx_or_parser, clean_name)
    delete_trigger_state(ctx_or_parser, clean_name)
    return True


def set_trigger_pulse(ctx_or_parser, name: str, pulse_ms: Any) -> int:
    clean_name = validate_trigger_name(name)
    trigger_def = load_trigger_def(ctx_or_parser, clean_name)
    if trigger_def is None:
        raise ValueError(f'trigger not found: !{clean_name}')

    value = _coerce_pulse_ms(pulse_ms)
    trigger_def.pulse_ms = value
    save_trigger_def(ctx_or_parser, trigger_def)

    trigger_state = load_trigger_state(ctx_or_parser, clean_name)
    trigger_state.pulse_ms = value
    save_trigger_state(ctx_or_parser, clean_name, trigger_state)
    return value


def create_event(ctx_or_parser, event_def: EventDef) -> EventDef:
    clean_name = validate_event_name(event_def.name)
    if load_event_def(ctx_or_parser, clean_name) is not None:
        raise ValueError('name exists')

    trigger_name = validate_trigger_name(event_def.trigger_name)
    if load_trigger_def(ctx_or_parser, trigger_name) is None:
        raise ValueError(f'trigger not found: !{trigger_name}')

    command = str(event_def.command or '').strip()
    if not command:
        raise ValueError('event command cannot be empty')
    if '\n' in command or '\r' in command:
        raise ValueError('event command must be one line')

    normalized = EventDef(
        name=clean_name,
        trigger_name=trigger_name,
        command=command,
    )
    save_event_def(ctx_or_parser, normalized)
    return normalized


def remove_event(ctx_or_parser, name: str) -> bool:
    clean_name = validate_event_name(name)
    if load_event_def(ctx_or_parser, clean_name) is None:
        return False
    delete_event_def(ctx_or_parser, clean_name)
    return True


def validate_trigger_write(path: str, value: Any) -> dict[str, Any]:
    name, field = validate_trigger_field_path(path)
    if field == 'state':
        raise ValueError('direct assignment to !<name>:state is not allowed')
    if field != 'pulse':
        raise ValueError(f'invalid trigger field: {field}')

    pulse_ms = _coerce_pulse_ms(value)
    return {
        'name': name,
        'field': field,
        'normalized_value': pulse_ms,
    }


def validate_event_write(path: str, value: Any) -> None:
    _ = value
    validate_event_path(path)
    raise ValueError('direct assignment to @... is not allowed')


def _coerce_pulse_ms(value: Any) -> int:
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
