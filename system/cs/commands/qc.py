from __future__ import annotations

import shlex

from system.cs.lib.qcall import QCallError, qc_raw
from system.cs.parser import HandlerResponse


command = "qc"
help_short = "qc[.profile] <output> <prompt...> -> raw model output to symbol"
help_full = (
    "qc[.<profile>] <output> <prompt...>\n"
    "\n"
    "Examples:\n"
    "  qc #out hello\n"
    "  qc #out $foo #bar baz\n"
    "  qc.grok #out $prompt\n"
    "\n"
    "Semantics:\n"
    "- first arg after command = output symbol\n"
    "- prompt tokens after that\n"
    "- symbol tokens in prompt are expanded\n"
    "- raw decoded output is written to out-symbol\n"
    "- accepted output types: string, list, dict\n"
    "- no buffer output\n"
    "- no chat history\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"qc parse error: {exc}")

    if len(parts) < 3:
        return HandlerResponse(error="usage: qc[.<profile>] <output> <prompt...>")

    command_token = parts[0]
    _output = parts[1]
    prompt = " ".join(parts[2:]).strip()

    if not prompt:
        return HandlerResponse(error="qc requires prompt")

    try:
        out = qc_raw(parser, command_token, prompt)
    except QCallError as exc:
        return HandlerResponse(error=str(exc))
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(result=out["decoded"])
