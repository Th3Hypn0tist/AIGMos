from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout


_history = InMemoryHistory()
_session = PromptSession(history=_history)


def _prompt() -> str:
    return "cs> "


def _render_lines(ctx) -> list[str]:
    out = ctx["state"].get("$SYSTEM.BUFFER")
    if out["error"]:
        return [f"[buffer read error] {out['error']}"]

    result = out["result"]
    if not result:
        return []

    if isinstance(result, dict):
        return [str(v) for _, v in sorted(result.items(), key=lambda item: int(item[0]))]

    return [str(result)]


def _append_buffer_line(ctx, text: str) -> None:
    out = ctx["state"].get("$SYSTEM.BUFFER")
    current = out["result"] or {}

    if not isinstance(current, dict):
        current = {}

    nums = []
    for key in current.keys():
        try:
            nums.append(int(key))
        except Exception:
            pass

    next_key = str((max(nums) if nums else 0) + 1)
    current[next_key] = text
    ctx["state"].set("$SYSTEM.BUFFER", current)


def _write_command_to_buffer(ctx, line: str) -> None:
    _append_buffer_line(ctx, f"cs> {line}")


def push_live_line(ctx, text: str) -> None:
    print(text, flush=True)


def render(ctx, force: bool = False) -> str:
    lines = _render_lines(ctx)

    if force:
        print("\033[2J\033[H", end="")

    if lines:
        print("\n".join(lines))

    return _prompt()


def read_input(ctx) -> str:
    with patch_stdout():
        return _session.prompt(_prompt())


def handle_input(ctx, command: str) -> None:
    line = (command or "").strip()
    if not line:
        return

    _write_command_to_buffer(ctx, line)
    _append_buffer_line(ctx, "")
    ctx["parser"].parse(line)
