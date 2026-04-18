from __future__ import annotations

import threading

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout

from system.layout.keymap import COMMAND_PREFIX, build_key_bindings, get_binding
from system.layout.ui_control import force_render, handle_immediate_ui_command


_history = InMemoryHistory()
_RUNTIME_KEY = "buffer_layout"


def _runtime(ctx) -> dict:
    runtime = ctx["parser"].runtime
    item = runtime.get(_RUNTIME_KEY)
    if not isinstance(item, dict):
        item = {
            "busy": False,
            "lock": threading.RLock(),
            "notice": "",
        }
        runtime[_RUNTIME_KEY] = item
    return item


def _is_busy(ctx) -> bool:
    return bool(_runtime(ctx).get("busy"))


def _set_busy(ctx, value: bool) -> None:
    item = _runtime(ctx)
    with item["lock"]:
        item["busy"] = bool(value)


def _set_notice(ctx, value: str) -> None:
    item = _runtime(ctx)
    with item["lock"]:
        item["notice"] = str(value or "").strip()


def _get_notice(ctx) -> str:
    item = _runtime(ctx)
    with item["lock"]:
        return str(item.get("notice") or "")


def _prompt(ctx) -> str:
    return "cs*> " if _is_busy(ctx) else "cs> "


def _get_buffer_lines(ctx) -> list[str]:
    out = ctx["state"].get("$SYSTEM.BUFFER")
    if out["error"]:
        return [f"[buffer read error] {out['error']}"]

    result = out["result"]
    if not result:
        return []

    if isinstance(result, dict):
        def _sort_key(item):
            key = str(item[0])
            try:
                return (0, int(key))
            except Exception:
                return (1, key)

        return [str(value) for _, value in sorted(result.items(), key=_sort_key)]

    return [str(result)]


def _render_lines(ctx) -> list[str]:
    lines = _get_buffer_lines(ctx)
    notice = _get_notice(ctx)
    if notice:
        return [notice, *lines]
    return lines


def _append_buffer_line(ctx, text: str) -> None:
    out = ctx["state"].get("$SYSTEM.BUFFER")
    current = out["result"] or {}

    if not isinstance(current, dict):
        current = {}

    nums = []
    for key in current.keys():
        try:
            nums.append(int(str(key)))
        except Exception:
            pass

    next_key = str((max(nums) if nums else 0) + 1)
    current[next_key] = text
    ctx["state"].set("$SYSTEM.BUFFER", current)


def append_line_to_buffer(ctx, text: str) -> None:
    _append_buffer_line(ctx, text)


def _write_command_to_buffer(ctx, line: str) -> None:
    _append_buffer_line(ctx, f"cs> {line}")


def push_live_line(_ctx, text: str) -> None:
    print(text, flush=True)


def render(ctx, force: bool = False) -> str:
    lines = _render_lines(ctx)

    if force:
        print("\033[2J\033[H", end="")

    if lines:
        print("\n".join(lines))

    return _prompt(ctx)


def read_input(ctx) -> str:
    session = PromptSession(
        history=_history,
        key_bindings=build_key_bindings(lambda slot: get_binding(ctx["state"], slot)),
    )
    with patch_stdout():
        return session.prompt(_prompt(ctx))


def _run_command_request(ctx, line: str) -> None:
    parser = ctx["parser"]
    try:
        parser.parse(line)
    finally:
        _set_busy(ctx, False)
        force_render(ctx)


def _start_command_request(ctx, line: str) -> bool:
    item = _runtime(ctx)

    with item["lock"]:
        if item.get("busy"):
            _set_notice(ctx, "[busy] command already in flight")
            force_render(ctx)
            return False

        item["busy"] = True
        item["notice"] = ""

    _write_command_to_buffer(ctx, line)
    _append_buffer_line(ctx, "")

    thread = threading.Thread(
        target=_run_command_request,
        args=(ctx, line),
        daemon=True,
        name="aigmos-buffer-layout-request",
    )
    thread.start()
    force_render(ctx)
    return True


def handle_input(ctx, command: str) -> None:
    raw = str(command or "")
    line = raw[len(COMMAND_PREFIX):] if raw.startswith(COMMAND_PREFIX) else raw
    line = line.strip()

    if not line:
        _set_notice(ctx, "")
        return

    if handle_immediate_ui_command(ctx, line):
        _set_notice(ctx, "")
        return

    _start_command_request(ctx, line)
