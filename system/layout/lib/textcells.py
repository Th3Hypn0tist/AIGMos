from __future__ import annotations

from typing import Any

from wcwidth import wcwidth


def char_cells(ch: str) -> int:
    try:
        width = int(wcwidth(str(ch or "")[:1]))
    except Exception:
        width = 1
    return width if width > 0 else 1


def text_cells(text: Any) -> int:
    return sum(char_cells(ch) for ch in str(text or ""))


def clip_cells(text: Any, width: int) -> str:
    limit = max(0, int(width or 0))
    if limit <= 0:
        return ""
    out: list[str] = []
    used = 0
    for ch in str(text or ""):
        cw = char_cells(ch)
        if used + cw > limit:
            break
        out.append(ch)
        used += cw
    return "".join(out)


def ljust_cells(text: Any, width: int) -> str:
    clipped = clip_cells(text, width)
    pad = max(0, int(width or 0) - text_cells(clipped))
    return clipped + (" " * pad)


def cursor_insert_index_for_cells(text: str, cell_pos: int) -> int:
    target = max(0, int(cell_pos or 0))
    used = 0
    idx = 0
    raw = str(text or "")
    while idx < len(raw) and used < target:
        used += char_cells(raw[idx])
        idx += 1
    return idx


def insert_cursor_marker(text: Any, cell_pos: int) -> str:
    raw = str(text or "")
    idx = cursor_insert_index_for_cells(raw, cell_pos)
    return raw[:idx] + "|" + raw[idx:]


__all__ = [
    "char_cells",
    "text_cells",
    "clip_cells",
    "ljust_cells",
    "cursor_insert_index_for_cells",
    "insert_cursor_marker",
]
