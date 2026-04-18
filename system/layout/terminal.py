from __future__ import annotations

import curses
import locale
from typing import Any

from . import input as layout_input
from . import render as layout_render
from .lib.textcells import clip_cells, ljust_cells, text_cells


def _addn(stdscr, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    if width <= 0 or y < 0 or x < 0:
        return
    try:
        stdscr.addnstr(y, x, text, width, attr)
    except curses.error:
        pass


def _project_payload(rect: dict[str, int], payload: dict[str, Any]) -> list[str]:
    w = max(0, int(rect.get("w", 0) or 0))
    h = max(0, int(rect.get("h", 0) or 0))
    if w <= 0 or h <= 0:
        return []
    rows = payload.get("screen_rows")
    if isinstance(rows, list):
        out = [ljust_cells(row, w) for row in rows[:h]]
        if len(out) < h:
            out.extend([" " * w] * (h - len(out)))
        return out
    lines = [str(item or "") for item in payload.get("lines", [])]
    align = str(payload.get("align", "left") or "left")
    va = str(payload.get("va", "bottom") or "bottom")
    visible = lines[:]
    if len(visible) > h:
        if va == "top":
            visible = visible[:h]
        elif va == "middle":
            start = max(0, (len(visible) - h) // 2)
            visible = visible[start : start + h]
        else:
            visible = visible[-h:]
    out = [" " * w for _ in range(h)]
    start_y = 0 if va == "top" else max(0, (h - len(visible)) // 2) if va == "middle" else max(0, h - len(visible))
    for i, raw in enumerate(visible):
        clipped = clip_cells(raw, w)
        clipped_w = text_cells(clipped)
        dx = max(0, (w - clipped_w) // 2) if align == "center" else max(0, w - clipped_w) if align == "right" else 0
        target = start_y + i
        if 0 <= target < h:
            out[target] = (" " * dx) + ljust_cells(clipped, w - dx)
    return out


def _draw_payload_full(stdscr, rect: dict[str, int], payload: dict[str, Any]) -> None:
    x, y = int(rect["x"]), int(rect["y"])
    w, rows = int(rect["w"]), _project_payload(rect, payload)
    for i, row in enumerate(rows):
        _addn(stdscr, y + i, x, row, w)


def _draw_payload_diff(stdscr, rect: dict[str, int], payload: dict[str, Any], prev_payload: dict[str, Any] | None = None) -> None:
    x, y = int(rect["x"]), int(rect["y"])
    w = int(rect["w"])
    if bool(payload.get("force_full_rect")):
        _draw_payload_full(stdscr, rect, payload)
        return
    row_updates = payload.get("row_updates")
    if isinstance(row_updates, list):
        for item in row_updates:
            if not isinstance(item, dict):
                continue
            local_y = int(item.get("y", -1) or -1)
            if local_y < 0 or local_y >= int(rect.get("h", 0) or 0):
                continue
            text = ljust_cells(item.get("text") or "", w)
            _addn(stdscr, y + local_y, x, text, w)
        return
    current_rows = _project_payload(rect, payload)
    previous_rows = _project_payload(rect, prev_payload or {}) if isinstance(prev_payload, dict) else []
    max_len = max(len(current_rows), len(previous_rows))
    for i in range(max_len):
        current = current_rows[i] if i < len(current_rows) else " " * w
        previous = previous_rows[i] if i < len(previous_rows) else " " * w
        if current != previous:
            _addn(stdscr, y + i, x, current, w)


def _draw(stdscr, ctx, *, full_clear: bool = False) -> tuple[str, int, int]:
    rows, cols = stdscr.getmaxyx()
    snapshot = layout_render.build_snapshot(ctx, cols, rows)
    redraw_all = bool(full_clear or snapshot.get("full_redraw"))
    if redraw_all:
        stdscr.erase()
        items = snapshot.get("drawables", [])
        for item in items:
            _draw_payload_full(stdscr, item.get("rect") or {}, item.get("payload") or {})
    else:
        items = snapshot.get("changed_drawables", [])
        for item in items:
            _draw_payload_diff(
                stdscr,
                item.get("rect") or {},
                item.get("payload") or {},
                item.get("prev_payload") if isinstance(item, dict) else None,
            )
    cursor = snapshot.get("cursor")
    try:
        curses.curs_set(1 if cursor else 0)
    except curses.error:
        pass
    if cursor:
        try:
            stdscr.move(int(cursor.get("y", 0)), int(cursor.get("x", 0)))
        except curses.error:
            pass
    stdscr.noutrefresh()
    curses.doupdate()
    return str(snapshot.get("active_handle") or ""), cols, rows


def _read_key(stdscr):
    try:
        return stdscr.get_wch()
    except curses.error:
        return -1


def _normalize_block_lines(text: str) -> list[str]:
    raw_lines = str(text or '').splitlines()
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    if not raw_lines:
        return []
    indents = [len(line) - len(line.lstrip(' ')) for line in raw_lines if line.strip()]
    trim = min(indents) if indents else 0
    return [line[trim:] for line in raw_lines]


def _draw_boot_splash(stdscr, flags: dict) -> None:
    rows, cols = stdscr.getmaxyx()
    stdscr.erase()
    art_lines = _normalize_block_lines(flags.get("boot_greeting_text") or "")
    log_lines = [str(item or "") for item in flags.get("boot_log_lines") or []]
    show_prompt = bool(flags.get("boot_startup_done"))
    prompt = "Press any key to continue" if show_prompt else ""

    art_width = max((text_cells(line) for line in art_lines), default=0)
    log_width = max((text_cells(line) for line in log_lines), default=0)
    prompt_width = text_cells(prompt) if prompt else 0
    content_width = max(art_width, log_width, prompt_width, 1)

    block_height = len(art_lines)
    if art_lines and log_lines:
        block_height += 1
    block_height += len(log_lines)
    if show_prompt:
        block_height += 2

    start_y = max(1, (rows - max(1, block_height)) // 2)
    y = start_y

    art_x = max(0, (cols - art_width) // 2) if art_width > 0 else 0
    log_x = max(0, (cols - log_width) // 2) if log_width > 0 else 0

    for line in art_lines:
        _addn(stdscr, y, art_x, clip_cells(line, max(1, cols - art_x)), max(0, cols - art_x))
        y += 1

    if art_lines and log_lines:
        y += 1

    for line in log_lines:
        _addn(stdscr, y, log_x, clip_cells(line, max(1, cols - log_x)), max(0, cols - log_x))
        y += 1

    if show_prompt:
        y += 1
        prompt_x = max(0, (cols - prompt_width) // 2)
        _addn(stdscr, min(rows - 1, y), prompt_x, prompt, max(0, cols - prompt_x), curses.A_BOLD)

    stdscr.noutrefresh()
    curses.doupdate()


def _maybe_run_boot_splash(stdscr, ctx) -> None:
    flags = ctx.setdefault('flags', {}) if isinstance(ctx, dict) else {}
    if not isinstance(flags, dict) or not flags.get('boot_splash_active'):
        return
    startup = ctx.get('boot_startup') if isinstance(ctx, dict) else None
    if callable(startup) and not flags.get('boot_startup_started'):
        import threading
        flags['boot_startup_started'] = True
        threading.Thread(target=startup, name='boot-startup', daemon=True).start()
    stdscr.timeout(50)
    while flags.get('running', True):
        _draw_boot_splash(stdscr, flags)
        key = _read_key(stdscr)
        if key == curses.KEY_RESIZE:
            continue
        if not flags.get('boot_startup_done'):
            continue
        if key != -1:
            break
    flags['boot_wait_for_key'] = False
    flags['boot_splash_active'] = False
    flags['force_render'] = True


def run(ctx) -> None:
    locale.setlocale(locale.LC_ALL, "")

    def main(stdscr) -> None:
        flags = ctx.setdefault("flags", {}) if isinstance(ctx, dict) else {}
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.timeout(25)
        try:
            curses.set_escdelay(25)
        except Exception:
            pass
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        _maybe_run_boot_splash(stdscr, ctx)
        last_state = None
        flags["force_render"] = True
        while flags.get("running", True):
            key = _read_key(stdscr)
            if key == curses.KEY_RESIZE:
                flags["force_render"] = True
                layout_input.handle_key(ctx, key)
            elif key in {27, ""}:
                next_key = _read_key(stdscr)
                if next_key != -1:
                    layout_input.handle_alt_key(ctx, next_key)
                else:
                    flags["force_render"] = True
            elif key != -1:
                layout_input.handle_key(ctx, key)
            if flags.get("force_render") or last_state is None:
                active = str(ctx.get("layout_runtime", {}).get("active_handle") or "")
                rows, cols = stdscr.getmaxyx()
                full_clear = last_state is None or last_state != (active, cols, rows)
                last_state = _draw(stdscr, ctx, full_clear=full_clear)
                flags["force_render"] = False
        flags["force_render"] = True
    curses.wrapper(main)


def queue_hard_redraw(ctx):
    flags = ctx.setdefault("flags", {}) if isinstance(ctx, dict) else {}
    flags["force_render"] = True
    flags["layout_hard_redraw"] = True
