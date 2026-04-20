from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv

from system.cs.lib.http_transport import is_symbol, request_text, resolve_value


command = "hpost"
help_short = 'hpost <output> <url|symbol> <raw-body...>'
help_full = """HTTP POST helper

current implementation:
- output first
- url may be literal or symbol
- body may be one symbol or raw trailing text
- response text is returned through the command framework

note:
- v40 canonical HTTP surface uses HTTP.POST, not hpost
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = parse_argv(
            line,
            usage="usage: hpost <output> <url|symbol> <raw-body...>",
            label="hpost",
            min_args=3,
        )
        _command = parts[0]
        _output = parts[1]
        src = parts[2]
        url = resolve_value(parser, src).strip()
        body = _get_body(parser, parts, line)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    result = request_text("POST", url, body=body)
    if not result["ok"]:
        return HandlerResponse(error=str(result['error'] or ""))

    return HandlerResponse(result=result['text'])


def _get_body(parser, parts: list[str], line: str) -> str:
    if len(parts) == 4 and is_symbol(parts[3]):
        return resolve_value(parser, parts[3])

    raw_parts = line.split(None, 3)
    if len(raw_parts) < 4:
        return ""

    return raw_parts[3]

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

