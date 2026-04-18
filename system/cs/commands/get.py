from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv
from system.cs.state_ops import get_optional


command = "get"
help_short = 'get <output> <symbol>'
help_full = """read one symbol for caller-side result handling

current implementation:
- command accepts an output token and one source symbol
- handler returns the resolved result to the command framework
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, _output, symbol = parse_argv(line, usage="usage: get <output> <symbol>", label="get", exact=2)
        return HandlerResponse(result=get_optional(parser.state, symbol))
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

