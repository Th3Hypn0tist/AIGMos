from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.lib.trigger.api import define_event_from_command

command = "on"
help_short = 'on !trigger @event "command"'
help_full = """bind one trigger to one named event and one quoted command payload

rules:
- event names must be unique
- payload is exactly one quoted command line
- direct assignment to @... is not allowed
- rm @name removes the event binding
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        define_event_from_command(parser, line)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))
    return HandlerResponse(buffer_output=str('[ok]' or ""))


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
