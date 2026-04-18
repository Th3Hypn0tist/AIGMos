from __future__ import annotations

import shlex

from system.cs.lib.http_helpers import is_symbol, request_text, resolve_value
from system.cs.parser import HandlerResponse


command = "hpost"
help_short = "hpost <output> <url|symbol> <raw-body...>"
help_full = (
    "hpost <output> <url|symbol> <raw-body...>\n"
    "\n"
    "Examples:\n"
    "  hpost #resp https://example.com/api {\"ping\":\"pong\"}\n"
    "  hpost #resp $MEM:url $MEM:body\n"
    "\n"
    "Semantics:\n"
    "- output first\n"
    "- url may be literal or symbol\n"
    "- body may be raw tail or one symbol\n"
    "- raw response text is written to output symbol\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"hpost parse error: {exc}")

    if len(parts) < 4:
        return HandlerResponse(error="usage: hpost <output> <url|symbol> <raw-body...>")

    _command = parts[0]
    _output = parts[1]
    src = parts[2]

    try:
        url = resolve_value(parser, src).strip()
        body = _get_body(parser, parts, line)
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    result = request_text("POST", url, body=body)
    if not result["ok"]:
        return HandlerResponse(error=result["error"])

    return HandlerResponse(result=result["text"])


def _get_body(parser, parts: list[str], line: str) -> str:
    if len(parts) == 4 and is_symbol(parts[3]):
        return resolve_value(parser, parts[3])

    raw_parts = line.split(None, 3)
    if len(raw_parts) < 4:
        return ""

    return raw_parts[3]
