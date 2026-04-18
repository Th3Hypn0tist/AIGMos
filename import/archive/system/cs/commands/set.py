from __future__ import annotations

import json

from system.cs.parser import HandlerResponse

command = "set"
help_short = "set <symbol> <value>"
help_full = "set symbol to value; tries json first then plain string"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) < 3:
        return HandlerResponse(error="usage: set <symbol> <value>")
    _, symbol, raw_value = parts
    try:
        value = json.loads(raw_value)
    except Exception:
        value = raw_value
    out = parser.state.set(symbol, value)
    if out["error"]:
        return HandlerResponse(error=out["error"])
    return HandlerResponse(buffer_output="[ok]")
