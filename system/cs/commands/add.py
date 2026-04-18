from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv
from system.cs.state_ops import get_optional, set_result
from system.cs.symbol_rules import require_symbol

command = "add"
help_short = 'add <target> <source>'
help_full = """append one value to $, #, or & target

rules:
- add applies only to $, #, and &
- & appends one new item
- $ and # append at next numeric child key
- existing non-numeric child keys make add fail
- runtime spaces ! @ % | are not valid add targets

examples:
  add &jobs run
  add $foo bar
  add #table:row $UM.sensor:temp
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, target, value = parse_argv(line, usage="usage: add <target> <value>", label="add", exact=2)
        require_symbol(target, allowed="$#&", role="add target")
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        current = get_optional(parser.state, target)

        if target[0] == "&":
            if current is None:
                current = []
            if not isinstance(current, list):
                return HandlerResponse(error=str('add target must be list' or ""))
            current.append(value)
        else:
            if current is None:
                current = {}
            if not isinstance(current, dict):
                return HandlerResponse(error=str('add target must be dict-like' or ""))

            for key in current.keys():
                if not str(key).isdigit():
                    return HandlerResponse(error=str('add target contains non-numeric keys' or ""))

            next_key = str(max((int(k) for k in current.keys()), default=-1) + 1)
            current[next_key] = value

        set_result(parser.state, target, current, writer="parser:add", op="add_append")
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

