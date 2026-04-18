from __future__ import annotations

from typing import Any

from system.layout.lib.border import content_rect
from system.layout.lib.handles import state_root_for_target
from system.layout.lib.payload import finalize_payload
from system.layout.lib.spec import flow_attr
from system.lib.q.qview import clear_q_state, render_q_lines
from system.layout.lib.scroll import handle_scroll_key

MODULE = "qmon"
DEFAULT_PROMPT = "cs> "
FOCUSABLE = True


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    cfg = dict(config or {})
    source_handle = str(cfg.get("source_handle") or cfg.get("target") or "").strip()
    base = state_root_for_target(source_handle)
    if not base:
        raise ValueError("qmon requires explicit target")
    return base, f"{base}:ch"


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    return {"min_h": 1, "scalable_y": True}


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    flow = flow_attr(MODULE, attrs)
    inner_rect = content_rect(attrs, rect)
    lines = render_q_lines(ctx, instance, int(inner_rect.get("w", 1) or 1), int(inner_rect.get("h", 1) or 1), flow)
    return finalize_payload(ctx, instance.handle, lines or [""], attrs, "q", rect)


def handle_key(ctx, module_handle: str, key: int) -> bool:
    from system.layout import input as layout_input

    ui = layout_input.get_module_ui(ctx, module_handle)
    if handle_scroll_key(ui, key, kind="q"):
        layout_input._mark_dirty(ctx)
        return True
    return False


def clear(ctx, module_handle: str, instance):
    return clear_q_state(ctx, module_handle, instance, clear_data=False)
