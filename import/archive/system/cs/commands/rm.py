from __future__ import annotations

from system.cs.lib.ops import remove_subtree, validate_symbol
from system.cs.parser import HandlerResponse
from system.runtime.runner import rm_runner
from system.runtime.runner_store import delete_runner_def

command = "rm"
help_short = "rm <target>"
help_full = "remove state symbol/subtree or runtime trigger/event binding"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: rm <target>")

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error="usage: rm <target>")

    try:
        root = validate_symbol(target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))

    if target.startswith("!"):
        triggers = parser.runtime.get("triggers")

        if triggers is None or not hasattr(triggers, "remove"):
            return HandlerResponse(error=f"trigger not found: {target}")

        removed = bool(triggers.remove(target[1:]))
        if not removed:
            return HandlerResponse(error=f"trigger not found: {target}")

        return HandlerResponse(buffer_output="[ok]")

    if target.startswith("@"):
        events = parser.runtime.get("events")
        if events is None or not hasattr(events, "remove_event"):
            return HandlerResponse(error=f"event not found: {target}")

        removed = bool(events.remove_event(target[1:]))
        if not removed:
            return HandlerResponse(error=f"event not found: {target}")

        return HandlerResponse(buffer_output="[ok]")

    try:
        if root == "%":
            removed = rm_runner(target)
            if not removed:
                return HandlerResponse(error=f"runner not found: {target}")
            delete_runner_def(parser.state, target)
            return HandlerResponse(buffer_output="[ok]")

        remove_subtree(parser.state, target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
