from __future__ import annotations

import shlex
from pathlib import Path

from system.cs.lib.qcall import (
    QCallError,
    q_chat,
    resolve_profile_name,
    system_prompt_symbol_for_profile,
)
from system.cs.parser import HandlerResponse


command = "q"
help_short = "q[.profile] <prompt...>"
help_full = (
    "q[.<profile>] <prompt...>\n"
    "\n"
    "Examples:\n"
    "  q hello\n"
    "  q $prompt\n"
    "  q.coder explain #code:main\n"
    "\n"
    "Semantics:\n"
    "- stateful chat\n"
    "- writes to active $CH history for the profile\n"
    "- returns assistant text to chat history\n"
)


_ROLES_DIR = Path(__file__).resolve().parents[2] / "prompts" / "roles"


def _set_force_render(parser) -> None:
    flags = parser.runtime.get("flags")
    if isinstance(flags, dict):
        flags["force_render"] = True
    parser.force_render = True


def _read_role_prompt(role_value: str) -> str:
    value = str(role_value or "").strip()
    if not value:
        return ""

    if "\n" in value:
        return value

    candidates: list[Path] = []
    if value.endswith(".md"):
        candidates.append(_ROLES_DIR / value)
    else:
        candidates.append(_ROLES_DIR / f"{value}.md")
        candidates.append(_ROLES_DIR / value)

    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()

    return value


def _apply_role_system_prompt(parser, command_token: str) -> None:
    profile_name = resolve_profile_name(parser, command_token, "q")

    symbols = [f"#SYSTEM:config:q:{profile_name}:role"]
    if profile_name != "default":
        symbols.append("#SYSTEM:config:q:default:role")

    role_value = ""
    for symbol in symbols:
        out = parser.state.get(symbol)
        if out["error"]:
            continue
        value = out["result"]
        if isinstance(value, str) and value.strip():
            role_value = value.strip()
            break

    if not role_value:
        return

    system_prompt = _read_role_prompt(role_value)
    target = system_prompt_symbol_for_profile(profile_name)
    set_out = parser.state.set(target, system_prompt)
    if set_out["error"]:
        raise QCallError(set_out["error"])


def pump_q_live(_parser):
    return None


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"q parse error: {exc}")

    if len(parts) < 2:
        return HandlerResponse(error="usage: q[.<profile>] <prompt...>")

    command_token = parts[0]
    prompt = " ".join(parts[1:]).strip()
    if not prompt:
        return HandlerResponse(error="q requires prompt")

    try:
        _apply_role_system_prompt(parser, command_token)
        out = q_chat(parser, command_token, prompt)
    except QCallError as exc:
        return HandlerResponse(error=str(exc))
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    _set_force_render(parser)
    return HandlerResponse(
        buffer_output=str(out.get("message") or ""),
        force_render=True,
    )
