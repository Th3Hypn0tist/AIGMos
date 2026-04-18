from __future__ import annotations

import shlex

from system.cs.lib.http_helpers import request_text, resolve_value
from system.cs.parser import HandlerResponse


command = "hget"
help_short = "hget <output> <url|symbol>"
help_full = (
    "hget <output> <url|symbol>\n"
    "\n"
    "Examples:\n"
    "  hget #resp https://example.com\n"
    "  hget #resp $MEM:url\n"
    "\n"
    "Semantics:\n"
    "- output first\n"
    "- url may be literal or symbol\n"
    "- raw response text is written to output symbol\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"hget parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: hget <output> <url|symbol>")

    _, _output, src = parts

    try:
        url = resolve_value(parser, src).strip()
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    result = request_text("GET", url)
    if not result["ok"]:
        return HandlerResponse(error=result["error"])

    return HandlerResponse(result=result["text"])
