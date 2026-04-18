# system/cs/commands/cat.py

from __future__ import annotations

from system.cs.lib.state_tree import dump_value, resolve_exact_or_branch
from system.cs.parser import HandlerResponse


command = "cat"
help_short = "cat <target>"
help_full = "show state value, branch dump, trigger definition, or event definition"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: cat <target>")

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error="usage: cat <target>")

    if target.startswith("!"):
        return _cat_trigger(target[1:], parser)

    if target.startswith("@"):
        return _cat_event(target[1:], parser)

    return _cat_state_target(target, parser)


def _cat_state_target(target: str, parser) -> HandlerResponse:
    try:
        value = resolve_exact_or_branch(parser, target)
    except RuntimeError as exc:
        return HandlerResponse(error=str(exc))

    if value is None:
        return HandlerResponse(error="target not found")

    return HandlerResponse(buffer_output=dump_value(value))


def _cat_trigger(name: str, parser) -> HandlerResponse:
    triggers = parser.runtime.get("triggers")

    if triggers is None or not hasattr(triggers, "get_def"):
        return HandlerResponse(error=f"trigger not found: !{name}")

    item = triggers.get_def(name)
    if item is None:
        return HandlerResponse(error=f"trigger not found: !{name}")

    current = parser.state.get(f"!{name}")
    value = current["result"] if not current["error"] else None

    lines = [
        f"!{name}",
        f"{item['left']} == {item['right']}",
        f"value: {value}",
    ]

    return HandlerResponse(buffer_output="\n".join(lines))


def _cat_event(name: str, parser) -> HandlerResponse:
    events = parser.runtime.get("events")
    if events is None or not hasattr(events, "get_event_def"):
        return HandlerResponse(error=f"event not found: @{name}")

    item = events.get_event_def(name)
    if item is None:
        return HandlerResponse(error=f"event not found: @{name}")

    lines = [f"@{name}"]

    if item["binds"]:
        lines.append("")
        lines.append("binds:")
        for trigger_name in item["binds"]:
            lines.append(f"!{trigger_name}")

    lines.append("")
    lines.append("commands:")
    for cmd in item["commands"]:
        lines.append(cmd)

    return HandlerResponse(buffer_output="\n".join(lines))
