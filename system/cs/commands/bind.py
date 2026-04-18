from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.layout.keymap import normalize_slot, set_binding, slot_label
from system.cs.runtime_ctx import force_render

command = "bind"
help_short = 'bind alt-1..alt-9|alt-0 <command...>'
help_full = """bind one alt hotkey slot to one raw command line

rules:
- allowed slots: alt-1..alt-9 and alt-0
- the bound value is stored exactly as one command line
- global/system bindings still take precedence over local instance bindings

example:
  bind alt-1 |Q
"""

def handler(line: str, parser) -> HandlerResponse:
    tokens = line.split()
    if len(tokens) < 3:
        return HandlerResponse(error=str('usage: bind alt-1..alt-9|alt-0 <command...>' or ""))

    slot_token = tokens[1]
    command_text = line.split(None, 2)[2].strip()

    try:
        slot = normalize_slot(slot_token)
        set_binding(parser.state, slot, command_text)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    force_render(parser)
    return HandlerResponse(buffer_output=str(f'[ok] {slot_label(slot)} -> {command_text}' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

