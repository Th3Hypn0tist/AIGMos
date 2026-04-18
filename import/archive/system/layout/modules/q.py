from __future__ import annotations

import threading

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout

from system.cs.lib.qcall import (
    QCallError,
    get_active_chat_symbol,
    get_active_profile,
    q_chat,
)
from system.layout.keymap import COMMAND_PREFIX, build_key_bindings, get_binding
from system.layout.ui_control import force_render, handle_immediate_ui_command


_history = InMemoryHistory()
_RUNTIME_KEY = "q_layout"


def _runtime(ctx) -> dict:
    runtime = ctx["parser"].runtime
    item = runtime.get(_RUNTIME_KEY)
    if not isinstance(item, dict):
        item = {
            "busy": False,
            "lock": threading.RLock(),
            "print_lock": threading.RLock(),
            "notice": "",
            "app": None,
            "stream_open": False,
            "pending_prompt": "",
            "pending_text": "",
            "printed_prompt": False,
            "printed_len": 0,
            "pending_index": 0,
        }
        runtime[_RUNTIME_KEY] = item
    return item


def _chat_symbol(ctx) -> str:
    return get_active_chat_symbol(ctx["parser"])


def _fmt_idx(idx: int) -> str:
    return f"{idx:05d}"


def _chat_key(idx: int) -> str:
    return _fmt_idx(idx)


def _sorted_chat_rows(ctx) -> list[tuple[int, dict]]:
    out = ctx["state"].get(_chat_symbol(ctx))
    if out["error"]:
        raise RuntimeError(out["error"])

    chat = out["result"] or {}
    if not isinstance(chat, dict):
        raise RuntimeError(f"invalid chat root: {type(chat).__name__}")

    rows: list[tuple[int, dict]] = []
    for key, value in chat.items():
        if not isinstance(value, dict):
            continue
        try:
            idx = int(str(key))
        except Exception:
            continue
        rows.append((idx, value))

    rows.sort(key=lambda item: item[0])
    return rows


def _next_chat_index(ctx) -> int:
    try:
        rows = _sorted_chat_rows(ctx)
    except Exception:
        return 0
    if not rows:
        return 0
    return rows[-1][0] + 1


def _update_chat_row(
    ctx,
    idx: int,
    *,
    prompt: str | None = None,
    response: str | None = None,
    done: int | None = None,
) -> None:
    symbol = _chat_symbol(ctx)

    out = ctx["state"].get(symbol)
    if out["error"]:
        return

    chat = out["result"] or {}
    if not isinstance(chat, dict):
        return

    key = _chat_key(idx)
    row = chat.get(key)
    if not isinstance(row, dict):
        row = {}

    if prompt is not None:
        row["prompt"] = str(prompt)
    if response is not None:
        row["response"] = str(response)
    if done is not None:
        row["done"] = int(done)

    chat[key] = row
    ctx["state"].set(symbol, chat)


def _active_pending_index(ctx) -> int | None:
    item = _runtime(ctx)
    with item["lock"]:
        if not item.get("stream_open"):
            return None
        return int(item.get("pending_index") or 0)


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


def _set_app(ctx, app) -> None:
    item = _runtime(ctx)
    with item["lock"]:
        item["app"] = app


def _get_app(ctx):
    item = _runtime(ctx)
    with item["lock"]:
        return item.get("app")


def _prompt(ctx) -> str:
    profile = get_active_profile(ctx["parser"])
    label = "q" if profile == "default" else profile
    suffix = "*" if _is_busy(ctx) else ""
    return f"Q[{label}{suffix}]> "


def _render_lines(ctx) -> list[str]:
    try:
        rows = _sorted_chat_rows(ctx)
    except Exception as exc:
        return [f"[chat read error] {exc}"]

    lines: list[str] = []
    notice = _get_notice(ctx)
    if notice:
        lines.append(notice)

    active_pending = _active_pending_index(ctx)

    for idx, item in rows:
        n = _fmt_idx(idx)
        prompt = str(item.get("prompt") or "")
        response = str(item.get("response") or "")
        done = 1 if item.get("done") else 0

        if active_pending is not None and idx == active_pending and done == 0:
            continue

        if prompt:
            lines.append(f"[{n}] q> {prompt}")

        if response:
            lines.append(f"[{n}] a> {response}")
        elif not done:
            lines.append(f"[{n}] a> ")

    return lines


def _reset_stream_paint(ctx) -> None:
    item = _runtime(ctx)
    with item["lock"]:
        if not item.get("stream_open"):
            return
        item["printed_prompt"] = False
        item["printed_len"] = 0


def render(ctx, force: bool = False) -> str:
    _reset_stream_paint(ctx)

    lines = _render_lines(ctx)

    if force:
        print("\033[2J\033[H", end="")

    if lines:
        print("\n".join(lines), flush=True)

    _flush_pending_stream(ctx)
    return _prompt(ctx)


def _run_in_terminal(ctx, fn) -> None:
    app = _get_app(ctx)
    if app is not None:
        try:
            app.run_in_terminal(fn, in_executor=False)
            return
        except Exception:
            pass
    fn()


def _print_locked(ctx, text: str = "", end: str = "\n") -> None:
    item = _runtime(ctx)

    def _do_print() -> None:
        with item["print_lock"]:
            print(text, end=end, flush=True)

    _run_in_terminal(ctx, _do_print)


def _ensure_stream_started(ctx) -> None:
    item = _runtime(ctx)

    with item["lock"]:
        app = item.get("app")
        stream_open = bool(item.get("stream_open"))
        printed_prompt = bool(item.get("printed_prompt"))
        prompt_text = str(item.get("pending_prompt") or "")
        pending_index = int(item.get("pending_index") or 0)

    if not stream_open or printed_prompt or app is None:
        return

    n = _fmt_idx(pending_index)
    _print_locked(ctx, f"[{n}] q> {prompt_text}")
    _print_locked(ctx, f"[{n}] a> ", end="")

    with item["lock"]:
        item["printed_prompt"] = True


def _flush_pending_stream(ctx) -> None:
    item = _runtime(ctx)

    _ensure_stream_started(ctx)

    with item["lock"]:
        app = item.get("app")
        stream_open = bool(item.get("stream_open"))
        printed_prompt = bool(item.get("printed_prompt"))
        pending_text = str(item.get("pending_text") or "")
        printed_len = int(item.get("printed_len") or 0)

    if app is None or not stream_open or not printed_prompt:
        return

    if len(pending_text) <= printed_len:
        return

    delta = pending_text[printed_len:]
    if delta:
        _print_locked(ctx, delta, end="")

    with item["lock"]:
        item["printed_len"] = len(pending_text)


def _open_stream(ctx, prompt_text: str) -> None:
    item = _runtime(ctx)
    next_idx = _next_chat_index(ctx)

    with item["lock"]:
        item["stream_open"] = True
        item["pending_prompt"] = str(prompt_text or "")
        item["pending_text"] = ""
        item["printed_prompt"] = False
        item["printed_len"] = 0
        item["pending_index"] = next_idx

    _update_chat_row(
        ctx,
        next_idx,
        prompt=prompt_text,
        response="",
        done=0,
    )

    _flush_pending_stream(ctx)


def _append_stream(ctx, final_text: str) -> None:
    item = _runtime(ctx)
    with item["lock"]:
        item["pending_text"] = str(final_text or "")
        idx = int(item.get("pending_index") or 0)
        text = item["pending_text"]

    _update_chat_row(
        ctx,
        idx,
        response=text,
        done=0,
    )

    _flush_pending_stream(ctx)


def _close_stream(ctx) -> None:
    item = _runtime(ctx)

    with item["lock"]:
        had_output = bool(item.get("printed_prompt"))
        item["stream_open"] = False
        item["pending_prompt"] = ""
        item["pending_text"] = ""
        item["printed_prompt"] = False
        item["printed_len"] = 0
        item["pending_index"] = 0

    if had_output:
        _print_locked(ctx, "")


def read_input(ctx) -> str:
    session = PromptSession(
        history=_history,
        key_bindings=build_key_bindings(lambda slot: get_binding(ctx["state"], slot)),
    )

    _set_app(ctx, session.app)
    _flush_pending_stream(ctx)

    try:
        with patch_stdout():
            return session.prompt(_prompt(ctx))
    finally:
        _set_app(ctx, None)


def _run_q_request(ctx, prompt_text: str) -> None:
    parser = ctx["parser"]

    old_buffer_suppress = parser.runtime.get("buffer_suppress", False)
    parser.runtime["buffer_suppress"] = True

    def _on_chunk(_chunk: str, final_text: str, _chat_symbol: str, _key: str) -> None:
        _append_stream(ctx, final_text)

    def _on_done(final_text: str, _chat_symbol: str, _key: str) -> None:
        item = _runtime(ctx)
        with item["lock"]:
            idx = int(item.get("pending_index") or 0)

        _append_stream(ctx, final_text)

        _update_chat_row(
            ctx,
            idx,
            response=str(final_text or ""),
            done=1,
        )

        _close_stream(ctx)
        force_render(ctx)

    try:
        q_chat(
            parser,
            "q",
            prompt_text,
            on_chunk=_on_chunk,
            on_done=_on_done,
        )
    except QCallError as exc:
        _close_stream(ctx)
        _set_notice(ctx, f"[error] {exc}")
        force_render(ctx)
    except Exception as exc:
        _close_stream(ctx)
        _set_notice(ctx, f"[error] {exc}")
        force_render(ctx)
    finally:
        parser.runtime["buffer_suppress"] = old_buffer_suppress
        _set_busy(ctx, False)
        force_render(ctx)


def _start_q_request(ctx, prompt_text: str) -> bool:
    item = _runtime(ctx)

    with item["lock"]:
        if item.get("busy"):
            _set_notice(ctx, "[busy] q request already in flight")
            force_render(ctx)
            return False

        item["busy"] = True
        item["notice"] = ""

    _open_stream(ctx, prompt_text)

    thread = threading.Thread(
        target=_run_q_request,
        args=(ctx, prompt_text),
        daemon=True,
        name="aigmos-q-layout-request",
    )
    thread.start()

    force_render(ctx)
    return True


def _run_parser_request(ctx, line: str) -> None:
    try:
        ctx["parser"].parse(line)
    finally:
        _set_busy(ctx, False)
        force_render(ctx)


def _start_parser_request(ctx, line: str) -> bool:
    item = _runtime(ctx)

    with item["lock"]:
        if item.get("busy"):
            _set_notice(ctx, "[busy] command already in flight")
            force_render(ctx)
            return False

        item["busy"] = True
        item["notice"] = ""

    thread = threading.Thread(
        target=_run_parser_request,
        args=(ctx, line),
        daemon=True,
        name="aigmos-q-layout-command",
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

    if raw.startswith(COMMAND_PREFIX) or line.startswith("/"):
        _set_notice(ctx, "")
        _start_parser_request(ctx, line)
        return

    _start_q_request(ctx, line)
