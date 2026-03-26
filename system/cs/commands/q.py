from __future__ import annotations

import shlex

from system.cs.lib.qcall import QCallError, q_chat
from system.cs.parser import HandlerResponse


command = "q"
help_short = "q[.profile] <prompt> -> chat to active/default profile"
help_full = (
    "q[.<profile>] <prompt>\n"
    "\n"
    "Examples:\n"
    "  q \"hello\"\n"
    "  q.grok \"hello\"\n"
    "\n"
    "Semantics:\n"
    "- no public target\n"
    "- plain q uses active profile, fallback = default\n"
    "- writes turns to $CH:q or $CH:<alias>\n"
    "- passes active chat history as context\n"
    "- writes AI output to $SYSTEM.BUFFER only when layout=buffer\n"
)


def _force_render(parser) -> None:
    flags = parser.runtime.get("flags")
    if isinstance(flags, dict):
        flags["force_render"] = True


def _is_buffer_layout(parser) -> bool:
    out = parser.state.get("$SYSTEM.LAYOUT")
    if out["error"]:
        return False
    return str(out["result"] or "").strip().lower() == "buffer"


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"q parse error: {exc}")

    if len(parts) < 2:
        return HandlerResponse(error="usage: q[.<profile>] <prompt>")

    command_token = parts[0]
    prompt = " ".join(parts[1:]).strip()
    if not prompt:
        return HandlerResponse(error="q requires prompt")

    try:
        out = q_chat(parser, command_token, prompt)
    except QCallError as exc:
        return HandlerResponse(error=str(exc))
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    _force_render(parser)

    if _is_buffer_layout(parser):
        return HandlerResponse(buffer_output=out["message"])

    return HandlerResponse()
