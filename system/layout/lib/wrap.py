from __future__ import annotations

import textwrap
from typing import Any

from .textcells import char_cells, clip_cells, text_cells


def wrap_text(text: Any, width: int) -> list[str]:
    width = max(1, int(width or 1))
    raw_lines = str(text or "").splitlines()
    if not raw_lines:
        return [""]
    out: list[str] = []
    for raw in raw_lines:
        if raw == "":
            out.append("")
            continue
        wrapped = textwrap.wrap(
            raw,
            width=width,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        out.extend(wrapped or [""])
    return out or [""]


def visible_wrap_lines(lines: list[str], width: int, height: int, flow: str = "bottom") -> list[str]:
    width = max(1, int(width or 1))
    height = max(1, int(height or 1))
    flow = str(flow or "bottom").strip().lower()
    if not lines:
        return [""]
    if flow == "top":
        out: list[str] = []
        for raw in lines:
            wrapped = wrap_text(raw, width)
            remaining = height - len(out)
            if remaining <= 0:
                break
            out.extend(wrapped[:remaining])
            if len(out) >= height:
                break
        return out or [""]
    collected: list[str] = []
    for raw in reversed(lines):
        wrapped = wrap_text(raw, width)
        for item in reversed(wrapped):
            if len(collected) >= height:
                break
            collected.append(item)
        if len(collected) >= height:
            break
    if not collected:
        return [""]
    collected.reverse()
    return collected


def visible_window_with_cursor(text: Any, cursor: int, width: int) -> tuple[str, int]:
    chars = list(str(text or ""))
    cursor = max(0, min(int(cursor or 0), len(chars)))
    width = max(1, int(width or 1))
    if not chars:
        return "", 0
    start = 0
    while start < cursor:
        window = "".join(chars[start:cursor])
        if text_cells(window) < width:
            break
        start += 1
    visible = clip_cells("".join(chars[start:]), width)
    local = text_cells("".join(chars[start:cursor]))
    return visible, max(0, min(width - 1, local))


def wrapped_window_with_cursor(text: Any, cursor: int, width: int, height: int) -> tuple[list[str], dict[str, int]]:
    raw = str(text or "")
    chars = list(raw)
    cursor = max(0, min(int(cursor or 0), len(chars)))
    width = max(1, int(width or 1))
    height = max(1, int(height or 1))

    lines: list[str] = []
    current: list[str] = []
    current_cells = 0
    cursor_line = 0
    cursor_col = 0

    for pos in range(len(chars) + 1):
        if pos == cursor:
            cursor_line = len(lines)
            cursor_col = max(0, min(width - 1, current_cells))
        if pos >= len(chars):
            break
        ch = chars[pos]
        if ch == "\n":
            lines.append("".join(current))
            current = []
            current_cells = 0
            continue
        cw = char_cells(ch)
        if current and current_cells + cw > width:
            lines.append("".join(current))
            current = [ch]
            current_cells = min(width, cw)
            continue
        current.append(ch)
        current_cells = min(width, current_cells + cw)

    lines.append("".join(current))
    if not lines:
        lines = [""]

    max_start = max(0, len(lines) - height)
    start = max(0, min(cursor_line - height + 1, max_start))
    if cursor_line < start:
        start = cursor_line
    end = min(len(lines), start + height)
    visible = lines[start:end] or [""]
    local_y = max(0, min(height - 1, cursor_line - start))
    local_x = max(0, min(width - 1, cursor_col))
    return visible, {"x": local_x, "y": local_y}


__all__ = [
    "wrap_text",
    "visible_wrap_lines",
    "visible_window_with_cursor",
    "wrapped_window_with_cursor",
]
