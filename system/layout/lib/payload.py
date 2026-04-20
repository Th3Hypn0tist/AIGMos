from __future__ import annotations

from typing import Any

from .border import BORDER_SIDE_ORDER, apply_border, border_enabled, border_sides, content_rect
from .editor import get_module_ui
from .textcells import clip_cells, ljust_cells, text_cells


def module_align(attrs: dict[str, Any]) -> str:
    align = str((attrs or {}).get("align") or "").strip().lower()
    return align if align in {"left", "center", "right"} else "left"


def module_flow(tag: str, attrs: dict[str, Any]) -> str:
    flow = str((attrs or {}).get("flow") or "").strip().lower()
    if flow in {"top", "middle", "bottom"}:
        return flow
    if str(tag or "").strip().lower() == "q":
        return "top"
    return "bottom"


def align_row(raw: str, width: int, align: str) -> str:
    width = max(0, int(width or 0))
    if width <= 0:
        return ""
    clipped = clip_cells(raw, width)
    clipped_w = text_cells(clipped)
    if align == "center":
        dx = max(0, (width - clipped_w) // 2)
    elif align == "right":
        dx = max(0, width - clipped_w)
    else:
        dx = 0
    return (" " * dx) + ljust_cells(clipped, width - dx)


def project_rows(lines: list[str], width: int, height: int, align: str = "left", va: str = "bottom") -> list[str]:
    width = max(0, int(width or 0))
    height = max(0, int(height or 0))
    if width <= 0 or height <= 0:
        return []
    visible = [str(item or "") for item in (lines or [""])]
    if len(visible) > height:
        if va == "top":
            visible = visible[:height]
        elif va == "middle":
            start = max(0, (len(visible) - height) // 2)
            visible = visible[start : start + height]
        else:
            visible = visible[-height:]
    out = [" " * width for _ in range(height)]
    if va == "top":
        start_y = 0
    elif va == "middle":
        start_y = max(0, (height - len(visible)) // 2)
    else:
        start_y = max(0, height - len(visible))
    for i, raw in enumerate(visible):
        target = start_y + i
        if 0 <= target < height:
            out[target] = align_row(raw, width, align)
    return out


def payload(lines: list[str], attrs: dict[str, Any], tag: str, rect: dict[str, int] | None = None) -> dict[str, Any]:
    out = {
        "lines": list(lines),
        "align": module_align(attrs),
        "va": module_flow(tag, attrs),
        "border": border_enabled(attrs),
        "border_sides": "".join(ch.upper() for ch in BORDER_SIDE_ORDER if ch in border_sides(attrs)),
    }
    if isinstance(rect, dict):
        if out["border"]:
            inner = content_rect(attrs, rect)
            inner_rows = project_rows(
                out["lines"],
                max(1, int(inner.get("w", 1) or 1)),
                max(1, int(inner.get("h", 1) or 1)),
                out["align"],
                out["va"],
            )
            out["screen_rows"] = apply_border(
                inner_rows,
                max(1, int(rect.get("w", 1) or 1)),
                max(1, int(rect.get("h", 1) or 1)),
                attrs=attrs,
            )
        else:
            out["screen_rows"] = project_rows(
                out["lines"],
                max(1, int(rect.get("w", 1) or 1)),
                max(1, int(rect.get("h", 1) or 1)),
                out["align"],
                out["va"],
            )
    return out


def finalize_payload(ctx, module_handle: str, lines: list[str], attrs: dict[str, Any], tag: str, rect: dict[str, int]) -> dict[str, Any]:
    out = payload(lines, attrs, tag, rect=rect)
    ui = get_module_ui(ctx, module_handle)
    current_rows = list(out.get("screen_rows") or [])
    width = max(1, int(rect.get("w", 1) or 1))
    previous_rows = ui.get("_last_screen_rows")
    updates: list[dict[str, Any]] = []
    if isinstance(previous_rows, list):
        max_len = max(len(previous_rows), len(current_rows))
        for i in range(max_len):
            prev = str(previous_rows[i]) if i < len(previous_rows) else (" " * width)
            curr = str(current_rows[i]) if i < len(current_rows) else (" " * width)
            if prev != curr:
                updates.append({"y": i, "text": curr})
    else:
        updates = [{"y": i, "text": row} for i, row in enumerate(current_rows)]
    out["row_updates"] = updates
    ui["_last_screen_rows"] = list(current_rows)
    return out


__all__ = [
    "module_align",
    "module_flow",
    "align_row",
    "project_rows",
    "payload",
    "finalize_payload",
]
