from __future__ import annotations

from typing import Any

from system.layout.lib import editor as layout_editor
from system.layout.lib.border import content_rect
from system.layout.lib.payload import finalize_payload
from system.layout.lib.spec import bool_attr, int_attr
from system.layout.lib.targets import layout_buffer_target
from system.layout.lib.textcells import insert_cursor_marker
from system.layout.lib.wrap import wrapped_window_with_cursor

MODULE = "cs"
DEFAULT_PROMPT = "cs> "
FOCUSABLE = True


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    cfg = dict(config or {})
    parent_layout = str(cfg.get('parent_layout') or '').strip()
    target_handle = str(cfg.get('target') or '').strip()
    if not target_handle:
        target_handle = parent_layout or str(handle or '').strip().split(':', 1)[0]
    target = layout_buffer_target(target_handle)
    return target, target


def _requested_lines(spec: dict[str, Any]) -> int:
    attrs = dict(spec.get('attrs') or {})
    return int_attr(attrs, 'lines', default=1, minimum=1)


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    return {"min_h": _requested_lines(spec), "scalable_y": False}


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    inner_rect = content_rect(attrs, rect)
    width = max(1, int(inner_rect.get("w", 1) or 1))
    height = max(1, int(inner_rect.get("h", _requested_lines(spec)) or _requested_lines(spec)))
    editor = layout_editor.get_editor(ctx, instance.handle)
    text = str(editor.get("buffer", "") or "")
    cursor = max(0, min(int(editor.get("cursor", 0) or 0), len(text)))
    visible_lines, local_cursor = wrapped_window_with_cursor(text, cursor, width, height)
    line_index = max(0, min(len(visible_lines) - 1, int(local_cursor.get("y", 0) or 0))) if visible_lines else 0
    lines = list(visible_lines or [""])
    lines[line_index] = insert_cursor_marker(lines[line_index], int(local_cursor.get("x", 0) or 0))
    out = finalize_payload(ctx, instance.handle, lines, attrs, MODULE, rect)
    border = bool_attr(attrs, 'border', False)
    out["cursor_local"] = {
        "x": int(local_cursor.get("x", 0) or 0) + (1 if border else 0),
        "y": int(local_cursor.get("y", 0) or 0) + (1 if border else 0),
    }
    out["force_full_rect"] = True
    out.pop("row_updates", None)
    return out


def handle_key(ctx, module_handle: str, key: int | str) -> bool:
    from system.layout import registry

    inst = registry.get_instance(ctx, module_handle)
    source_handle = registry.get_parent_layout_for_instance(ctx, module_handle) or module_handle
    target_handle = str(getattr(inst, "config", {}).get("target") or "").strip() or source_handle
    return layout_editor.handle_key(
        ctx,
        module_handle,
        key,
        source_handle=source_handle,
        target_handle=target_handle,
    )


def clear(ctx, module_handle: str, instance):
    return layout_editor.clear_editor(ctx, module_handle)
