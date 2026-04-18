from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.lib.ops import remove_subtree
from system.cs.symbol_rules import require_symbol
from system.runtime.runner import rm_runner
from system.runtime.runner_store import delete_runner_def
from system.cs.runtime_ctx import get_ctx
from system.lib.trigger.api import remove_runtime_object
from system.state.api import delete_value, list_symbols

command = "rm"
help_short = 'rm <target>'
help_full = """remove one state symbol, subtree, or runtime object

runtime forms:
- rm !trigger
- rm @event
- rm %runner
- rm |layout

notes:
- rm is the destructive path for runtime objects
- bare runtime handles remove the runtime object itself
- nested runtime paths remove only that runtime subtree/value
"""


def _delete_runtime_subtree(state, target: str) -> bool:
    clean = str(target or '').strip()
    if not clean:
        return False

    symbols = list_symbols(state)
    prefix = clean + ':'
    matches = [symbol for symbol in symbols if symbol == clean or symbol.startswith(prefix)]
    if not matches:
        return False

    for symbol in sorted(matches, key=len, reverse=True):
        out = delete_value(state, symbol, writer="parser:rm", op="rm_runtime_delete")
        if out.get("error"):
            raise ValueError(out["error"])
    return True



def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error=str('usage: rm <target>' or ""))

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error=str('usage: rm <target>' or ""))

    try:
        root = require_symbol(target)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        if root in {'!', '@'}:
            if ':' not in target:
                removed = bool(remove_runtime_object(parser, target))
                if not removed:
                    kind = 'trigger' if target.startswith('!') else 'event'
                    return HandlerResponse(error=str(f'{kind} not found: {target}' or ""))
                return HandlerResponse(buffer_output=str('[ok]' or ""))

            removed = _delete_runtime_subtree(parser.state, target)
            if not removed:
                return HandlerResponse(error=str(f'target not found: {target}' or ""))
            return HandlerResponse(buffer_output=str('[ok]' or ""))

        if root == "%":
            if ':' not in target:
                removed = rm_runner(target)
                if not removed:
                    return HandlerResponse(error=str(f'runner not found: {target}' or ""))
                delete_runner_def(parser.state, target)
                return HandlerResponse(buffer_output=str('[ok]' or ""))

            removed = _delete_runtime_subtree(parser.state, target)
            if not removed:
                return HandlerResponse(error=str(f'target not found: {target}' or ""))
            return HandlerResponse(buffer_output=str('[ok]' or ""))

        if root == "|":
            if ':' not in target:
                from system.layout import registry as layout_registry  # type: ignore
                ctx = get_ctx(parser)
                removed = layout_registry.remove_instance(ctx, target)
                if not removed:
                    return HandlerResponse(error=str(f'layout not found: {target}' or ""))
                return HandlerResponse(buffer_output=str('[ok]' or ""))

            removed = _delete_runtime_subtree(parser.state, target)
            if not removed:
                return HandlerResponse(error=str(f'target not found: {target}' or ""))
            return HandlerResponse(buffer_output=str('[ok]' or ""))

        remove_subtree(parser.state, target, writer="parser:rm", op="rm_remove_subtree")
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str('[ok]' or ""))



def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
