# system/cs/commands/mv.py
from __future__ import annotations

from system.cs.lib.ops import move_subtree, validate_symbol
from system.cs.parser import HandlerResponse

command = "mv"
help_short = "mv <source> <target>"
help_full = "rename or move state-side symbol or subtree. runtime spaces are not allowed"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) != 3:
        return HandlerResponse(error="usage: mv <source> <target>")
    _, source, target = parts
    try:
        validate_symbol(source)
        validate_symbol(target)
        move_subtree(parser.state, source, target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))
    return HandlerResponse(buffer_output="[ok]")
