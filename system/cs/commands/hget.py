from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv

from system.cs.lib.http_transport import request_text, resolve_value


command = "hget"
help_short = 'hget <output> <url|symbol>'
help_full = """HTTP GET helper

current implementation:
- output first
- url may be literal or symbol
- response text is returned through the command framework

note:
- v40 canonical HTTP surface uses HTTP.GET, not hget
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, _output, src = parse_argv(
            line,
            usage="usage: hget <output> <url|symbol>",
            label="hget",
            exact=2,
        )
        url = resolve_value(parser, src).strip()
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    result = request_text("GET", url)
    if not result["ok"]:
        return HandlerResponse(error=str(result['error'] or ""))

    return HandlerResponse(result=result['text'])

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

