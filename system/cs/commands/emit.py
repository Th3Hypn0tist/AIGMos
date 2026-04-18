from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.symbol_rules import require_prefixed_token
from system.cs.runtime_ctx import get_events, get_trigger_bus

command = "emit"
help_short = 'emit @event | emit !trigger'
help_full = """helper: emit one event directly or push one trigger into the trigger bus

note:
- emit is outside the locked v40 canonical command surface
"""

def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error=str('usage: emit @event | emit !trigger' or ""))

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error=str('usage: emit @event | emit !trigger' or ""))

    try:
        if target.startswith("@"):
            require_prefixed_token(target, "@", role="event")
            events = get_events(parser)
            if events is None or not hasattr(events, "emit_event"):
                return HandlerResponse(error=str('events runtime unavailable' or ""))
            events.emit_event(target[1:], parser)
            return HandlerResponse(buffer_output=str('[ok]' or ""))

        if target.startswith("!"):
            require_prefixed_token(target, "!", role="trigger")
            trigger_bus = get_trigger_bus(parser)
            if trigger_bus is None or not hasattr(trigger_bus, "put"):
                return HandlerResponse(error=str('trigger bus runtime unavailable' or ""))
            trigger_bus.put(target[1:])
            return HandlerResponse(buffer_output=str('[ok]' or ""))
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(error=str('emit target must start with @ or !' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

