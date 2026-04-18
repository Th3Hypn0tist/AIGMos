from __future__ import annotations

from typing import Any

from system.state.api import delete_value, list_symbols, read_value, write_value
from system.lib.trigger.names import validate_event_name, validate_trigger_name
from system.lib.trigger.types import EventDef, TriggerDef, TriggerState

TRIGGER_DEFS_ROOT = '#SYSTEM:runtime:triggers'
EVENT_DEFS_ROOT = '#SYSTEM:runtime:events'
TRIGGER_STATE_ROOT = '#SYSTEM:runtime:trigger_state'


def _get_state(ctx_or_parser):
    if hasattr(ctx_or_parser, 'state'):
        return getattr(ctx_or_parser, 'state')
    if hasattr(ctx_or_parser, 'read_state') and hasattr(ctx_or_parser, 'write_state'):
        return ctx_or_parser
    if isinstance(ctx_or_parser, dict):
        state = ctx_or_parser.get('state')
        if state is not None:
            return state
    runtime = getattr(ctx_or_parser, 'runtime', None)
    if isinstance(runtime, dict):
        ctx = runtime.get('ctx')
        if isinstance(ctx, dict) and ctx.get('state') is not None:
            return ctx['state']
    raise ValueError('state unavailable')


def _trigger_def_symbol(name: str) -> str:
    clean = validate_trigger_name(name)
    return f'{TRIGGER_DEFS_ROOT}:{clean}'


def _event_def_symbol(name: str) -> str:
    clean = validate_event_name(name)
    return f'{EVENT_DEFS_ROOT}:{clean}'


def _trigger_state_symbol(name: str) -> str:
    clean = validate_trigger_name(name)
    return f'!{clean}:state'


def _trigger_pulse_symbol(name: str) -> str:
    clean = validate_trigger_name(name)
    return f'!{clean}:pulse'


def _trigger_runtime_symbol(name: str) -> str:
    clean = validate_trigger_name(name)
    return f'{TRIGGER_STATE_ROOT}:{clean}'


def load_trigger_def(ctx_or_parser, name: str) -> TriggerDef | None:
    state = _get_state(ctx_or_parser)
    data = read_value(state, _trigger_def_symbol(name), None)
    if not isinstance(data, dict):
        return None
    return TriggerDef.from_dict(validate_trigger_name(name), data)


def save_trigger_def(ctx_or_parser, trigger_def: TriggerDef) -> TriggerDef:
    state = _get_state(ctx_or_parser)
    out = write_value(
        state,
        _trigger_def_symbol(trigger_def.name),
        trigger_def.to_dict(),
        writer=_writer('trigger', trigger_def.name),
        op='trigger_save_def',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))
    return trigger_def


def delete_trigger_def(ctx_or_parser, name: str) -> None:
    state = _get_state(ctx_or_parser)
    out = delete_value(
        state,
        _trigger_def_symbol(name),
        writer=_writer('trigger', name),
        op='trigger_delete_def',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))


def load_trigger_state(ctx_or_parser, name: str) -> TriggerState:
    state = _get_state(ctx_or_parser)
    clean = validate_trigger_name(name)

    visible_state = read_value(state, _trigger_state_symbol(clean), None)
    visible_pulse = read_value(state, _trigger_pulse_symbol(clean), None)
    internal = read_value(state, _trigger_runtime_symbol(clean), None)

    payload = dict(internal) if isinstance(internal, dict) else {}
    if visible_state is not None:
        payload['state'] = visible_state
    if visible_pulse is not None:
        payload['pulse_ms'] = visible_pulse

    return TriggerState.from_dict(payload)


def save_trigger_state(ctx_or_parser, name: str, trigger_state: TriggerState) -> TriggerState:
    state = _get_state(ctx_or_parser)
    clean = validate_trigger_name(name)
    writer = _writer('trigger', clean)

    full_payload = trigger_state.to_dict()

    out = write_value(
        state,
        _trigger_state_symbol(clean),
        full_payload['state'],
        writer=writer,
        op='trigger_save_state_field',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))

    out = write_value(
        state,
        _trigger_pulse_symbol(clean),
        str(full_payload['pulse_ms']),
        writer=writer,
        op='trigger_save_pulse_field',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))

    out = write_value(
        state,
        _trigger_runtime_symbol(clean),
        full_payload,
        writer=writer,
        op='trigger_save_runtime_state',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))

    return trigger_state


def delete_trigger_state(ctx_or_parser, name: str) -> None:
    state = _get_state(ctx_or_parser)
    clean = validate_trigger_name(name)
    writer = _writer('trigger', clean)

    for symbol, op in (
        (_trigger_state_symbol(clean), 'trigger_delete_state_field'),
        (_trigger_pulse_symbol(clean), 'trigger_delete_pulse_field'),
        (_trigger_runtime_symbol(clean), 'trigger_delete_runtime_state'),
    ):
        out = delete_value(state, symbol, writer=writer, op=op)
        if out.get('error'):
            raise ValueError(str(out['error']))


def list_trigger_names(ctx_or_parser) -> list[str]:
    state = _get_state(ctx_or_parser)
    prefix = TRIGGER_DEFS_ROOT + ':'
    names = {
        symbol[len(prefix):]
        for symbol in list_symbols(state)
        if symbol.startswith(prefix)
    }
    return sorted(name for name in names if name)


def load_event_def(ctx_or_parser, name: str) -> EventDef | None:
    state = _get_state(ctx_or_parser)
    data = read_value(state, _event_def_symbol(name), None)
    if not isinstance(data, dict):
        return None
    return EventDef.from_dict(validate_event_name(name), data)


def save_event_def(ctx_or_parser, event_def: EventDef) -> EventDef:
    state = _get_state(ctx_or_parser)
    out = write_value(
        state,
        _event_def_symbol(event_def.name),
        event_def.to_dict(),
        writer=_writer('event', event_def.name),
        op='event_save_def',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))
    return event_def


def delete_event_def(ctx_or_parser, name: str) -> None:
    state = _get_state(ctx_or_parser)
    out = delete_value(
        state,
        _event_def_symbol(name),
        writer=_writer('event', name),
        op='event_delete_def',
    )
    if out.get('error'):
        raise ValueError(str(out['error']))


def list_event_names(ctx_or_parser) -> list[str]:
    state = _get_state(ctx_or_parser)
    prefix = EVENT_DEFS_ROOT + ':'
    names = {
        symbol[len(prefix):]
        for symbol in list_symbols(state)
        if symbol.startswith(prefix)
    }
    return sorted(name for name in names if name)


def list_events_for_trigger(ctx_or_parser, trigger_name: str) -> list[EventDef]:
    clean_trigger = validate_trigger_name(trigger_name)
    results: list[EventDef] = []
    for name in list_event_names(ctx_or_parser):
        event_def = load_event_def(ctx_or_parser, name)
        if event_def is not None and event_def.trigger_name == clean_trigger:
            results.append(event_def)
    results.sort(key=lambda item: item.name)
    return results


def _writer(kind: str, name: str) -> str:
    clean = str(name or '').strip() or 'unknown'
    return f'trigger.store:{kind}:{clean}'
