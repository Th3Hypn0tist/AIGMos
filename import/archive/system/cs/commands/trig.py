from __future__ import annotations

from system.cs.parser import HandlerResponse

command = "trig"
help_short = "trig !name <left> == <right>"
help_full = "register passive equality trigger"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) != 3:
        return HandlerResponse(error="usage: trig !name <left> == <right>")

    _, target, expr = parts

    if not target.startswith("!") or len(target) == 1:
        return HandlerResponse(error="trigger target must start with !")

    if "==" not in expr:
        return HandlerResponse(error="only == is supported")

    left, right = expr.split("==", 1)
    left = left.strip()
    right = right.strip()

    if not left:
        return HandlerResponse(error="left side missing")

    if not right:
        return HandlerResponse(error="right side missing")

    if left[0] not in "$#&%@!":
        return HandlerResponse(error="left side must be a symbol")

    parser.runtime["triggers"].add(target[1:], left, right)
    return HandlerResponse(buffer_output="[ok]")
