from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse



command = "echo"
help_short = 'echo <message>'
help_full = """write one raw message to buffer output

note:
- convenience helper for local output; does not write state by itself"""

def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error=str('usage: echo <message>' or ""))

    return HandlerResponse(buffer_output=str(parts[1] or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

