from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from system.lib.trigger.cron_eval import is_cron_due, mark_cron_fired
from system.lib.trigger.expr_eval import eval_expr
from system.lib.trigger.onchange import evaluate_onchange
from system.lib.trigger.pulse import can_fire, mark_fired
from system.lib.trigger.store import (
    _get_state,
    list_trigger_names,
    load_trigger_def,
    load_trigger_state,
    save_trigger_state,
)
from system.lib.trigger.types import (
    TRIGGER_KIND_CRON,
    TRIGGER_KIND_EXPR,
    TRIGGER_KIND_ONCHANGE,
    TriggerDef,
    TriggerEvalResult,
    TriggerState,
)
from system.state.api import read_value

Resolver = Callable[[str], Any]


def evaluate_trigger(
    ctx_or_parser,
    trigger_def: TriggerDef,
    now_ms: int,
    now_dt: datetime,
    resolver: Resolver | None = None,
) -> TriggerEvalResult:
    state = load_trigger_state(ctx_or_parser, trigger_def.name)
    result: TriggerEvalResult

    if trigger_def.kind == TRIGGER_KIND_EXPR:
        result = evaluate_expr_trigger(ctx_or_parser, trigger_def, state, now_ms, resolver)
    elif trigger_def.kind == TRIGGER_KIND_ONCHANGE:
        result = evaluate_onchange_trigger(ctx_or_parser, trigger_def, state, now_ms, resolver)
    elif trigger_def.kind == TRIGGER_KIND_CRON:
        result = evaluate_cron_trigger(ctx_or_parser, trigger_def, state, now_ms, now_dt)
    else:
        state.state = '0'
        result = TriggerEvalResult(active=False, fired=False, reason=f'unknown:{trigger_def.kind}')

    save_trigger_state(ctx_or_parser, trigger_def.name, state)
    return result


def evaluate_expr_trigger(
    ctx_or_parser,
    trigger_def: TriggerDef,
    state: TriggerState,
    now_ms: int,
    resolver: Resolver | None = None,
) -> TriggerEvalResult:
    resolve = resolver or _state_resolver(ctx_or_parser)
    active = bool(eval_expr(trigger_def.expr, resolve))
    state.state = '1' if active else '0'
    fired = bool(active and can_fire(now_ms, state.last_fire_ms, state.pulse_ms))
    if fired:
        mark_fired(state, now_ms)
    return TriggerEvalResult(active=active, fired=fired, reason='expr')


def evaluate_onchange_trigger(
    ctx_or_parser,
    trigger_def: TriggerDef,
    state: TriggerState,
    now_ms: int,
    resolver: Resolver | None = None,
) -> TriggerEvalResult:
    resolve = resolver or _state_resolver(ctx_or_parser)
    current = resolve(trigger_def.source)
    result = evaluate_onchange(current, state)
    if result.fired and not can_fire(now_ms, state.last_fire_ms, state.pulse_ms):
        result = TriggerEvalResult(active=result.active, fired=False, reason='pulse')
    if result.fired:
        mark_fired(state, now_ms)
    return result


def evaluate_cron_trigger(
    ctx_or_parser,
    trigger_def: TriggerDef,
    state: TriggerState,
    now_ms: int,
    now_dt: datetime,
) -> TriggerEvalResult:
    due = bool(is_cron_due(trigger_def.cron_spec, now_dt, state))
    state.state = '1' if due else '0'
    fired = bool(due and can_fire(now_ms, state.last_fire_ms, state.pulse_ms))
    if fired:
        mark_fired(state, now_ms)
        mark_cron_fired(state, trigger_def.cron_spec, now_dt)
    return TriggerEvalResult(active=due, fired=fired, reason='cron')


def run_trigger_cycle(
    ctx_or_parser,
    now_ms: int,
    now_dt: datetime,
    resolver: Resolver | None = None,
) -> list[str]:
    fired: list[str] = []
    for name in list_trigger_names(ctx_or_parser):
        trigger_def = load_trigger_def(ctx_or_parser, name)
        if trigger_def is None:
            continue
        result = evaluate_trigger(ctx_or_parser, trigger_def, now_ms, now_dt, resolver)
        if result.fired:
            fired.append(trigger_def.name)
    return fired


def _state_resolver(ctx_or_parser) -> Resolver:
    state = _get_state(ctx_or_parser)

    def _resolve(symbol: str) -> Any:
        return read_value(state, symbol, None)

    return _resolve
