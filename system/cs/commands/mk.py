from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_tail
from system.cs.state_ops import get_optional, set_result
from system.cs.symbol_rules import require_symbol

command = "mk"
help_short = 'mk <target>'
help_full = """create an empty state node

rules:
- $ and # create empty dict-like nodes
- & creates an empty list
- runtime spaces ! @ % | are not valid mk targets
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        target = parse_tail(line, usage="usage: mk <target>")
        root = require_symbol(target)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    if root in ("%", "!", "@"):
        return HandlerResponse(error=str('mk does not create runtimes' or ""))

    try:
        if get_optional(parser.state, target) is not None:
            return HandlerResponse(error=str('target already exists' or ""))

        value = [] if root == "&" else {}
        set_result(parser.state, target, value, writer="parser:mk", op="mk_create")
        return HandlerResponse(buffer_output=str("[ok]" or ""))

    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

