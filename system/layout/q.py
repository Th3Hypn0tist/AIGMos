from __future__ import annotations

import json

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout

from system.cs.lib.qcall import get_active_chat_symbol, get_active_profile


_history = InMemoryHistory()
_session = PromptSession(history=_history)


def _prompt(ctx) -> str:
    profile = get_active_profile(ctx["parser"])
    label = "q" if profile == "default" else profile
    return f"Q[{label}]> "


def _render_lines(ctx) -> list[str]:
    symbol = get_active_chat_symbol(ctx["parser"])
    out = ctx["state"].get(symbol)
    if out["error"]:
        return [f"[chat read error] {out['error']}"]

    result = out["result"]
    if not isinstance(result, dict):
        return []

    turns = result.get("turns")
    if not isinstance(turns, list):
        return []

    lines = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue

        q_text = ((turn.get("q") or {}).get("text"))
        a_text = ((turn.get("a") or {}).get("text"))

        if q_text not in (None, ""):
            lines.append(f"you> {q_text}")
        if a_text not in (None, ""):
            lines.append(f"ai> {a_text}")

    return lines


def render(ctx, force: bool = False) -> str:
    lines = _render_lines(ctx)

    if force:
        print("\033[2J\033[H", end="")

    if lines:
        print("\n".join(lines))

    return _prompt(ctx)


def read_input(ctx) -> str:
    with patch_stdout():
        return _session.prompt(_prompt(ctx))


def handle_input(ctx, command: str) -> None:
    line = (command or "").strip()
    if not line:
        return

    if line.startswith("/"):
        ctx["parser"].parse(line)
        return

    ctx["parser"].parse(f"q {json.dumps(line, ensure_ascii=False)}")
