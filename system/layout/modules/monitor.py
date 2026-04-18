from __future__ import annotations

from typing import Any

from system.layout.lib.border import content_rect
from system.layout.lib.payload import finalize_payload
from system.layout.lib.scroll import handle_scroll_key
from system.layout.lib.view_resolvers import render_monitor_lines

MODULE = "monitor"
DEFAULT_PROMPT = "cs> "
FOCUSABLE = True


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    cfg = dict(config or {})
    target = str(cfg.get("target") or f"{handle}:buffer").strip()
    return target, target


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    return {"min_h": 1, "scalable_y": True}


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    lines = render_monitor_lines(ctx, instance, spec, content_rect(attrs, rect)) or [""]
    return finalize_payload(ctx, instance.handle, lines, attrs, MODULE, rect)


def handle_key(ctx, module_handle: str, key: int) -> bool:
    from system.layout import input as layout_input

    ui = layout_input.get_module_ui(ctx, module_handle)
    if handle_scroll_key(ui, key, kind="monitor"):
        layout_input._mark_dirty(ctx)
        return True
    return False


def clear(ctx, module_handle: str, instance):
    from system.layout import input as layout_input
    from system.layout import state as layout_state

    target = str(getattr(instance, "view_target", "") or getattr(instance, "primary_target", "") or "").strip()
    if target:
        layout_state.set_value(ctx, target, "")
    ui = layout_input.get_module_ui(ctx, module_handle)
    ui["follow"] = True
    ui["scroll"] = 0
    return True
