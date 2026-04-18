from __future__ import annotations

from system.cs.parser import HandlerResponse

command = "on"
help_short = "on !trigger @event <command>"
help_full = "append command to event and bind event to trigger"


def handler(line: str, parser) -> HandlerResponse:
    line = line.strip()

    if not line.startswith("on "):
        return HandlerResponse(error="usage: on !trigger @event <command>")

    rest = line[3:].strip()
    if not rest:
        return HandlerResponse(error="usage: on !trigger @event <command>")

    parts = rest.split(maxsplit=2)
    if len(parts) != 3:
        return HandlerResponse(error="usage: on !trigger @event <command>")

    trigger, event, cmd = parts

    if not trigger.startswith("!") or len(trigger) == 1:
        return HandlerResponse(error="trigger must start with !")

    if not event.startswith("@") or len(event) == 1:
        return HandlerResponse(error="event must start with @")

    parser.runtime["events"].bind(trigger[1:], event[1:], cmd)
    return HandlerResponse(buffer_output="[ok]")
