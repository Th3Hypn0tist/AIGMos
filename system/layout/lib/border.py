from __future__ import annotations

from typing import Any

from .textcells import ljust_cells


def border_enabled(attrs: dict[str, Any] | None) -> bool:
    value = str((attrs or {}).get("border") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def content_rect(attrs: dict[str, Any] | None, rect: dict[str, int] | None) -> dict[str, int]:
    base = dict(rect or {})
    if not border_enabled(attrs):
        return base
    return {
        "x": int(base.get("x", 0) or 0) + 1,
        "y": int(base.get("y", 0) or 0) + 1,
        "w": max(1, int(base.get("w", 1) or 1) - 2),
        "h": max(1, int(base.get("h", 1) or 1) - 2),
    }


def draw_border_frame(width: int, height: int) -> list[str]:
    width = max(1, int(width or 1))
    height = max(1, int(height or 1))
    frame = [[" " for _ in range(width)] for _ in range(height)]
    if width == 1 and height == 1:
        return ["+"]
    for x in range(width):
        frame[0][x] = "-"
        frame[height - 1][x] = "-"
    for y in range(height):
        frame[y][0] = "|"
        frame[y][width - 1] = "|"
    frame[0][0] = "+"
    frame[0][width - 1] = "+"
    frame[height - 1][0] = "+"
    frame[height - 1][width - 1] = "+"
    return ["".join(row) for row in frame]


def apply_border(rows: list[str], width: int, height: int) -> list[str]:
    width = max(1, int(width or 1))
    height = max(1, int(height or 1))
    frame = [list(row) for row in draw_border_frame(width, height)]
    if width >= 3 and height >= 3:
        inner_w = width - 2
        inner_h = height - 2
        visible = [ljust_cells(row, inner_w) for row in (rows or [""])[:inner_h]]
        if len(visible) < inner_h:
            visible.extend([" " * inner_w] * (inner_h - len(visible)))
        for iy in range(inner_h):
            row = visible[iy]
            for ix, ch in enumerate(row[:inner_w]):
                frame[iy + 1][ix + 1] = ch
    return ["".join(row) for row in frame]


__all__ = [
    "border_enabled",
    "content_rect",
    "draw_border_frame",
    "apply_border",
]
