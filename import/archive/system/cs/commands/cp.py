# system/cs/commands/cp.py
from __future__ import annotations

from system.cs.lib.ops import copy_subtree, validate_symbol
from system.cs.parser import HandlerResponse

command = "cp"
help_short = "cp <source> <target>"
help_full = "copy state-side symbol or subtree. runtime spaces are not allowed"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) != 3:
        return HandlerResponse(error="usage: cp <source> <target>")
    _, source, target = parts
    try:
        validate_symbol(source)
        validate_symbol(target)
        copy_subtree(parser.state, source, target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))
    return HandlerResponse(buffer_output="[ok]")
