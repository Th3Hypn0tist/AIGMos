from __future__ import annotations

import re
import shlex
import time
from datetime import datetime

from system.lib.trigger.cron_spec import normalize_cron_spec
from system.lib.trigger.event_runtime import dispatch_events_for_trigger
from system.lib.trigger.expr_parse import parse_expr
from system.lib.trigger.lifecycle import (
    create_event,
    create_trigger,
    remove_event,
    remove_trigger,
)
from system.lib.trigger.names import validate_event_name, validate_trigger_name
from system.lib.trigger.runtime import run_trigger_cycle
from system.lib.trigger.types import (
    TRIGGER_KIND_CRON,
    TRIGGER_KIND_EXPR,
    TRIGGER_KIND_ONCHANGE,
    EventDef,
    TriggerDef,
)

_ON_RE = re.compile(r'^on\s+(!\S+)\s+(@\S+)\s+"(.*)"\s*$')


def define_trigger_from_command(ctx_or_parser, line: str) -> TriggerDef:
    tokens = shlex.split(str(line or '').strip())
    if len(tokens) < 3 or tokens[0] != 'trig':
        raise ValueError('usage: trig !name <expr> | trig !name onchange <ref> | trig !name cron "spec"')

    target = validate_trigger_name(tokens[1])
    if tokens[2] == 'onchange':
        if len(tokens) != 4:
            raise ValueError('usage: trig !name onchange <ref>')
        source = str(tokens[3] or '').strip()
        if not source or source[0] not in '$#&%@!|':
            raise ValueError('onchange source must be a canonical reference')
        return create_trigger(ctx_or_parser, TriggerDef(name=target, kind=TRIGGER_KIND_ONCHANGE, source=source))

    if tokens[2] == 'cron':
        if len(tokens) != 4:
            raise ValueError('usage: trig !name cron "spec"')
        spec = normalize_cron_spec(tokens[3])
        return create_trigger(ctx_or_parser, TriggerDef(name=target, kind=TRIGGER_KIND_CRON, cron_spec=spec))

    expr = str(line or '').strip().split(None, 2)[2].strip()
    if not expr:
        raise ValueError('trigger expression cannot be empty')
    parse_expr(expr, strict_grouping=True)
    return create_trigger(ctx_or_parser, TriggerDef(name=target, kind=TRIGGER_KIND_EXPR, expr=expr))


def define_event_from_command(ctx_or_parser, line: str) -> EventDef:
    match = _ON_RE.fullmatch(str(line or '').strip())
    if not match:
        raise ValueError('usage: on !trigger @event "command"')
    trigger_name = validate_trigger_name(match.group(1))
    event_name = validate_event_name(match.group(2))
    command = str(match.group(3) or '').strip()
    if not command:
        raise ValueError('event command cannot be empty')
    return create_event(ctx_or_parser, EventDef(name=event_name, trigger_name=trigger_name, command=command))


def remove_runtime_object(ctx_or_parser, path: str) -> bool:
    raw = str(path or '').strip()
    if raw.startswith('!'):
        return remove_trigger(ctx_or_parser, raw[1:])
    if raw.startswith('@'):
        return remove_event(ctx_or_parser, raw[1:])
    raise ValueError(f'unsupported runtime object: {path}')


def run_cycle(ctx_or_parser, *, now_ms: int | None = None, now_dt: datetime | None = None, parser=None) -> list[str]:
    use_now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    use_now_dt = datetime.now() if now_dt is None else now_dt
    fired = run_trigger_cycle(ctx_or_parser, use_now_ms, use_now_dt)
    dispatched: list[str] = []
    for trigger_name in fired:
        dispatched.extend(dispatch_events_for_trigger(ctx_or_parser, trigger_name, parser=parser))
    return dispatched
