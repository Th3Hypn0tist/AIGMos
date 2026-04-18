from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.command_args import parse_command_output_tail_raw
from system.lib.q.errors import QCallError
from system.lib.q.worker import enqueue_qc_command


command = "qc"
help_short = 'qc[.profile] <output> <prompt...>'
help_full = """stateless structured q call

rules:
- output target is explicit
- no chat history is written
- accepted decoded output types: string, list, dict
- execution is queued through the shared q/qc worker

examples:
  qc #out hello
  qc.coder #out $prompt
"""


def handler(line: str, parser) -> HandlerResponse:
    try:
        command_token, output_symbol, prompt = parse_command_output_tail_raw(
            line,
            usage="usage: qc[.<profile>] <output> <prompt...>",
            label="qc",
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""), force_render=True)

    if not isinstance(output_symbol, str) or output_symbol[:1] not in "$#&":
        return HandlerResponse(error=str('qc output must start with $, # or &' or ""), force_render=True)

    try:
        enqueue_qc_command(parser, command_token, output_symbol, prompt)
    except QCallError as exc:
        return HandlerResponse(error=str(str(exc) or ""), force_render=True)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""), force_render=True)

    return HandlerResponse(buffer_output=str(""), force_render=True)


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
