from __future__ import annotations

from typing import Any

from system.lib.trigger.store import list_events_for_trigger
from system.lib.trigger.types import EventDef


def dispatch_events_for_trigger(ctx_or_parser, trigger_name: str, parser=None) -> list[str]:
    parser_obj = parser or _get_parser(ctx_or_parser)
    dispatched: list[str] = []
    for event_def in list_events_for_trigger(ctx_or_parser, trigger_name):
        dispatch_event(ctx_or_parser, event_def, parser=parser_obj)
        dispatched.append(event_def.name)
    return dispatched


def dispatch_event(ctx_or_parser, event_def: EventDef, parser=None) -> None:
    parser_obj = parser or _get_parser(ctx_or_parser)
    if parser_obj is None or not hasattr(parser_obj, 'parse'):
        raise ValueError('parser unavailable for event dispatch')
    err = parser_obj.parse(event_def.command)
    if err:
        raise RuntimeError(str(err))


def _get_parser(ctx_or_parser) -> Any:
    if hasattr(ctx_or_parser, 'parse'):
        return ctx_or_parser
    if isinstance(ctx_or_parser, dict):
        parser = ctx_or_parser.get('parser')
        if parser is not None:
            return parser
    runtime = getattr(ctx_or_parser, 'runtime', None)
    if isinstance(runtime, dict):
        ctx = runtime.get('ctx')
        if isinstance(ctx, dict):
            return ctx.get('parser')
    return None
