from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.layout.keymap import SLOT_ORDER, list_bindings, slot_label

command = "binds"
help_short = 'binds'
help_full = """list current alt hotkey bindings

shows alt-1..alt-9 and alt-0 with bound command or [unbound]"""

def _format_bindings(parser) -> str:
    bindings = list_bindings(parser.state)
    lines = []

    for slot in SLOT_ORDER:
        label = slot_label(slot)
        bound = bindings.get(slot, "")
        lines.append(f"{label} -> {bound or '[unbound]'}")

    return "\n".join(lines)


def handler(line: str, parser) -> HandlerResponse:
    tokens = line.split()
    if len(tokens) != 1:
        return HandlerResponse(error=str('usage: binds' or ""))
    return HandlerResponse(buffer_output=str(_format_bindings(parser) or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

