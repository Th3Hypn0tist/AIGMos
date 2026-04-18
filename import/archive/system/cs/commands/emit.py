from __future__ import annotations

from system.cs.parser import HandlerResponse

command = "emit"
help_short = "emit @event | emit !trigger"
help_full = "emit event directly or push trigger into trigger bus"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: emit @event | emit !trigger")

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error="usage: emit @event | emit !trigger")

    if target.startswith("@"):
        parser.runtime["events"].emit_event(target[1:], parser)
        return HandlerResponse(buffer_output="[ok]")

    if target.startswith("!"):
        parser.runtime["trigger_bus"].put(target[1:])
        return HandlerResponse(buffer_output="[ok]")

    return HandlerResponse(error="emit target must start with @ or !")
