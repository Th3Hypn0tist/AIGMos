from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.state_ops import get_optional
from system.cs.runtime_ctx import get_ctx, get_events, get_triggers
from system.lib.symbols import dump_value, resolve_raw_exact

command = "cat"
help_short = 'cat <target>'
help_full = """show one resolved target in readable form

target kinds:
- $ # & -> dump current value
- !name -> show trigger detail
- @name -> show event detail
- |name -> show layout instance detail

notes:
- cat does not accept bare roots: ! @ |
"""

def handler(line: str, parser):
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error=str("usage: cat <target>" or ""))

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error=str("usage: cat <target>" or ""))

    if target in {"|", "!", "@"}:
        return HandlerResponse(error=str("root target not supported" or ""))

    if target.startswith("!"):
        return _cat_trigger(target[1:], parser)

    if target.startswith("@"):
        return _cat_event(target[1:], parser)

    if target.startswith(("|", "¤")):
        return _cat_layout(target, parser)

    return _cat_state_target(target, parser)


def _cat_state_target(target: str, parser):
    try:
        value = resolve_raw_exact(parser.state, target)
    except RuntimeError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    if value is None:
        return HandlerResponse(error=str("target not found" or ""))

    return HandlerResponse(buffer_output=str(dump_value(value) or ""))


def _cat_trigger(name: str, parser):
    clean = str(name or "").strip()
    if not clean:
        return HandlerResponse(error=str("trigger not found" or ""))

    triggers = get_triggers(parser)
    if triggers is None or not hasattr(triggers, "get_def"):
        return HandlerResponse(error=str(f"trigger not found: !{clean}" or ""))

    item = triggers.get_def(clean)
    if item is None:
        return HandlerResponse(error=str(f"trigger not found: !{clean}" or ""))

    lines = [
        f"name: !{clean}",
        f"left: {item.get('left', '')}",
        f"right: {item.get('right', '')}",
        f"value: {get_optional(parser.state, f'!{clean}')}",
    ]
    return HandlerResponse(buffer_output=str("\n".join(lines) or ""))


def _cat_event(name: str, parser):
    clean = str(name or "").strip()
    if not clean:
        return HandlerResponse(error=str("event not found" or ""))

    events = get_events(parser)
    if events is None or not hasattr(events, "get_event_def"):
        return HandlerResponse(error=str(f"event not found: @{clean}" or ""))

    item = events.get_event_def(clean)
    if item is None:
        return HandlerResponse(error=str(f"event not found: @{clean}" or ""))

    binds = item.get("binds") or []
    commands = item.get("commands") or []

    lines = [f"name: @{clean}"]

    lines.append("binds:")
    if binds:
        for trigger_name in binds:
            lines.append(f"!{trigger_name}")
    else:
        lines.append("-")

    lines.append("commands:")
    if commands:
        for command in commands:
            lines.append(str(command))
    else:
        lines.append("-")

    return HandlerResponse(buffer_output=str("\n".join(lines) or ""))


def _cat_layout(target: str, parser):
    from system.layout import registry as layout_registry  # type: ignore

    ctx = get_ctx(parser)
    raw = str(target or "").strip()
    if raw.startswith("¤"):
        raw = "|" + raw[1:]

    if ":" in raw[1:]:
        return _cat_state_target(raw, parser)

    try:
        clean = layout_registry.normalize_handle(raw)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        value = resolve_raw_exact(parser.state, clean)
    except RuntimeError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    if value is not None:
        if isinstance(value, dict):
            payload = dict(value)
        else:
            payload = {"value": value}

        if layout_registry.has_layout_binding(ctx, clean):
            payload.setdefault("modules", layout_registry.get_bound_layout_modules(ctx, clean))
            payload.setdefault("type", "layout")
        elif layout_registry.has_instance(ctx, clean):
            payload.setdefault("layout_owner", layout_registry.get_parent_layout_for_instance(ctx, clean) or "")
            payload.setdefault("type", "instance")

        return HandlerResponse(buffer_output=str(dump_value(payload) or ""))

    if layout_registry.has_layout_binding(ctx, clean) or layout_registry.has_instance(ctx, clean):
        return HandlerResponse(buffer_output=str(dump_value({}) or ""))

    return HandlerResponse(error=str("target not found" or ""))


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
