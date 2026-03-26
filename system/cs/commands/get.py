from __future__ import annotations

from system.cs.parser import HandlerResponse


command = "get"
help_short = "get <output> <symbol>"
help_full = "read symbol and write result to output target"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split()
    if len(parts) != 3:
        return HandlerResponse(error="usage: get <output> <symbol>")

    _, _output, symbol = parts

    out = parser.state.get(symbol)
    if out["error"]:
        return HandlerResponse(error=out["error"])

    return HandlerResponse(result=out["result"])
