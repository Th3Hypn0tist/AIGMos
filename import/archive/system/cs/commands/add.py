from __future__ import annotations

from system.cs.parser import HandlerResponse

command = "add"
help_short = "add <target> <value>"
help_full = "append value to $, # or & target"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) != 3:
        return HandlerResponse(error="usage: add <target> <value>")

    _, target, value = parts

    if not target or target[0] not in "$#&":
        return HandlerResponse(error="add target must start with $, # or &")

    out = parser.state.get(target)
    if out["error"]:
        return HandlerResponse(error=out["error"])

    current = out["result"]

    if target[0] == "&":
        if current is None:
            current = []
        if not isinstance(current, list):
            return HandlerResponse(error="add target must be list")
        current.append(value)
    else:
        if current is None:
            current = {}
        if not isinstance(current, dict):
            return HandlerResponse(error="add target must be dict-like")

        for key in current.keys():
            if not str(key).isdigit():
                return HandlerResponse(error="add target contains non-numeric keys")

        next_key = str(max((int(k) for k in current.keys()), default=-1) + 1)
        current[next_key] = value

    set_out = parser.state.set(target, current)
    if set_out["error"]:
        return HandlerResponse(error=set_out["error"])

    return HandlerResponse(buffer_output="[ok]")
