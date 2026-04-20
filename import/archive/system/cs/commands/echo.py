from __future__ import annotations

from system.cs.parser import HandlerResponse

command = "echo"
help_short = "echo <message>"
help_full = "write message to buffer"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: echo <message>")

    return HandlerResponse(buffer_output=parts[1])
