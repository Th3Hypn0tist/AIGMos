from __future__ import annotations

from typing import Any

from .textcells import ljust_cells


FULL_BORDER_VALUES = {"1", "true", "yes", "on"}
BORDER_SIDE_ORDER = ("n", "s", "w", "e")
_VALID_BORDER_SIDES = frozenset(BORDER_SIDE_ORDER)


def border_sides(attrs: dict[str, Any] | None) -> set[str]:
    value = str((attrs or {}).get("border") or "").strip().lower()
    if value in FULL_BORDER_VALUES:
        return set(_VALID_BORDER_SIDES)
    return {ch for ch in value if ch in _VALID_BORDER_SIDES}


def border_enabled(attrs: dict[str, Any] | None) -> bool:
    return bool(border_sides(attrs))


def border_padding(attrs: dict[str, Any] | None) -> dict[str, int]:
    sides = border_sides(attrs)
    return {
        "top": 1 if "n" in sides else 0,
        "bottom": 1 if "s" in sides else 0,
        "left": 1 if "w" in sides else 0,
        "right": 1 if "e" in sides else 0,
    }


def content_rect(attrs: dict[str, Any] | None, rect: dict[str, int] | None) -> dict[str, int]:
    base = dict(rect or {})
    pad = border_padding(attrs)
    base_x = int(base.get("x", 0) or 0)
    base_y = int(base.get("y", 0) or 0)
    base_w = max(0, int(base.get("w", 0) or 0))
    base_h = max(0, int(base.get("h", 0) or 0))
    inner_w = max(0, base_w - int(pad["left"]) - int(pad["right"]))
    inner_h = max(0, base_h - int(pad["top"]) - int(pad["bottom"]))
    return {
        "x": base_x + int(pad["left"]),
        "y": base_y + int(pad["top"]),
        "w": inner_w,
        "h": inner_h,
    }


def draw_border_frame(width: int, height: int, attrs: dict[str, Any] | None = None) -> list[str]:
    width = max(0, int(width or 0))
    height = max(0, int(height or 0))
    if width <= 0 or height <= 0:
        return []
    sides = border_sides(attrs)
    frame = [[" " for _ in range(width)] for _ in range(height)]
    if not sides:
        return ["".join(row) for row in frame]
    if "n" in sides:
        for x in range(width):
            frame[0][x] = "-"
    if "s" in sides:
        for x in range(width):
            frame[height - 1][x] = "-"
    if "w" in sides:
        for y in range(height):
            frame[y][0] = "|"
    if "e" in sides:
        for y in range(height):
            frame[y][width - 1] = "|"
    if "n" in sides and "w" in sides:
        frame[0][0] = "+"
    if "n" in sides and "e" in sides:
        frame[0][width - 1] = "+"
    if "s" in sides and "w" in sides:
        frame[height - 1][0] = "+"
    if "s" in sides and "e" in sides:
        frame[height - 1][width - 1] = "+"
    return ["".join(row) for row in frame]


def apply_border(rows: list[str], width: int, height: int, attrs: dict[str, Any] | None = None) -> list[str]:
    width = max(0, int(width or 0))
    height = max(0, int(height or 0))
    if width <= 0 or height <= 0:
        return []
    frame = [list(row) for row in draw_border_frame(width, height, attrs=attrs)]
    inner = content_rect(attrs, {"x": 0, "y": 0, "w": width, "h": height})
    inner_x = int(inner.get("x", 0) or 0)
    inner_y = int(inner.get("y", 0) or 0)
    inner_w = max(0, int(inner.get("w", 0) or 0))
    inner_h = max(0, int(inner.get("h", 0) or 0))
    if inner_w <= 0 or inner_h <= 0:
        return ["".join(row) for row in frame]
    visible = [ljust_cells(row, inner_w) for row in (rows or [""])[:inner_h]]
    if len(visible) < inner_h:
        visible.extend([" " * inner_w] * (inner_h - len(visible)))
    for iy in range(inner_h):
        row = visible[iy]
        target_y = inner_y + iy
        if not (0 <= target_y < height):
            continue
        for ix, ch in enumerate(row[:inner_w]):
            target_x = inner_x + ix
            if 0 <= target_x < width:
                frame[target_y][target_x] = ch
    return ["".join(row) for row in frame]


__all__ = [
    "BORDER_SIDE_ORDER",
    "FULL_BORDER_VALUES",
    "border_enabled",
    "border_padding",
    "border_sides",
    "content_rect",
    "draw_border_frame",
    "apply_border",
]
