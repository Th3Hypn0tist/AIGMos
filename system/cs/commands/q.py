from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.runtime_ctx import get_layout_caller_handle
from system.lib.q.errors import QCallError
from system.lib.q.worker import enqueue_q_command
from system.layout.lib.targets import resolve_querytarget

command = 'q'
help_short = 'q[.profile] <target> <prompt...>'
help_full = """stateful chat/query dispatch

rules:
- target is explicit
- dispatches query asynchronously
- does not return successful assistant output to command buffer
- queue truth lives in #SYSTEM:Qcue
- q-root live fields are active-render cache only
- queued items do not overwrite active q-root live state
- one global active slot per q runtime root; queued FIFO per profile alias

examples:
  q |:q hello
  q |HELP:q explain #HELP:README.md
  q.coder |:q refactor this
"""


def _parse_q_target_prompt(line: str) -> tuple[str, str, str]:
    raw = str(line or '').strip()
    parts = raw.split(maxsplit=2)
    if len(parts) < 3:
        raise ValueError('usage: q[.profile] <target> <prompt...>')
    command_token, target, prompt = parts[0], parts[1], parts[2]
    if not prompt or not prompt.strip():
        raise ValueError('q requires prompt')
    return command_token, target, prompt


def handler(line: str, parser):
    try:
        command_token, raw_target, prompt = _parse_q_target_prompt(line)
    except Exception as exc:
        return HandlerResponse(error=str(exc or ''), force_render=True)

    try:
        q_root = resolve_querytarget(raw_target, get_layout_caller_handle(parser))
        enqueue_q_command(parser, command_token, q_root, prompt)
    except QCallError as exc:
        return HandlerResponse(error=str(exc or ''), force_render=True)
    except Exception as exc:
        return HandlerResponse(error=str(exc or ''), force_render=True)

    return HandlerResponse(buffer_output='', force_render=True)


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
