from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.layout.keymap import clear_binding, normalize_slot, slot_label
from system.cs.runtime_ctx import force_render

command = "unbind"
help_short = 'unbind alt-1..alt-9|alt-0'
help_full = """remove one alt hotkey binding

example:
  unbind alt-1"""

def handler(line: str, parser) -> HandlerResponse:
    tokens = line.split()
    if len(tokens) != 2:
        return HandlerResponse(error=str('usage: unbind alt-1..alt-9|alt-0' or ""))

    try:
        slot = normalize_slot(tokens[1])
        clear_binding(parser.state, slot)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    force_render(parser)
    return HandlerResponse(buffer_output=str(f'[ok] {slot_label(slot)} cleared' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

