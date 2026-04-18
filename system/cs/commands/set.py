from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import json

from system.cs.symbol_rules import require_symbol
from system.state.api import write_value


command = "set"
help_short = 'set <symbol> <value>'
help_full = """write one value to one symbol

rules:
- command first tries json decoding
- fallback is raw string value
- symbol must be a valid writable target
"""

def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=2)
    if len(parts) < 3:
        return HandlerResponse(error=str('usage: set <symbol> <value>' or ""))

    _, symbol, raw_value = parts

    try:
        require_symbol(symbol)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        value = json.loads(raw_value)
    except Exception:
        value = raw_value

    out = write_value(parser.state, symbol, value, writer="parser:set", op="set")
    if out["error"]:
        return HandlerResponse(error=str(str(out['error']) or ""))

    return HandlerResponse(buffer_output=str("[ok]" or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

