from __future__ import annotations

import curses
from typing import Any

from system.layout.lib.border import content_rect
from system.layout.lib.payload import finalize_payload, module_flow
from system.layout.lib.view_resolvers import render_list_lines
from system.layout.lib.wrap import visible_wrap_lines
from system.state.api import read_value

MODULE = "list"
DEFAULT_PROMPT = "cs> "
FOCUSABLE = True


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    return f"{handle}:buffer", f"{handle}:buffer"


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    return {"min_h": 1, "scalable_y": True}


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    flow = module_flow(MODULE, attrs)
    lines = render_list_lines(ctx, instance)
    inner_rect = content_rect(attrs, rect)
    visible = visible_wrap_lines(lines, max(1, inner_rect.get("w", 1)), max(1, inner_rect.get("h", 1)), flow)
    return finalize_payload(ctx, instance.handle, visible, attrs, MODULE, rect)


def handle_key(ctx, module_handle: str, key: int) -> bool:
    from system.layout import input as layout_input
    from system.layout import registry

    ui = layout_input.get_module_ui(ctx, module_handle)
    inst = registry.get_instance(ctx, module_handle)
    value = read_value(ctx.get("state"), inst.primary_target, None) if ctx.get("state") is not None else None
    size = len(value) if isinstance(value, (dict, list)) else 0
    if size <= 0:
        return False
    selected = int(ui.get("selected", 0) or 0)
    if key == curses.KEY_UP:
        ui["selected"] = max(0, selected - 1)
        layout_input._mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_DOWN:
        ui["selected"] = min(size - 1, selected + 1)
        layout_input._mark_dirty(ctx, module_handle)
        return True
    return False
