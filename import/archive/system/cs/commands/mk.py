from __future__ import annotations

from system.cs.lib.ops import validate_symbol
from system.cs.parser import HandlerResponse

command = "mk"
help_short = "mk <target>"
help_full = "create empty state node: $/# => {}, & => []. runtime spaces are not allowed"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: mk <target>")
    target = parts[1].strip()
    try:
        root = validate_symbol(target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))

    if root in ("%", "!", "@"):
        return HandlerResponse(error="mk does not create runtimes")

    out = parser.state.get(target)
    if out["error"]:
        return HandlerResponse(error=out["error"])
    if out["result"] is not None:
        return HandlerResponse(error="target already exists")

    value = [] if root == "&" else {}
    out = parser.state.set(target, value)
    if out["error"]:
        return HandlerResponse(error=out["error"])
    return HandlerResponse(buffer_output="[ok]")
