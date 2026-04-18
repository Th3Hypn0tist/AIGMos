from __future__ import annotations

from typing import Any

from .. import state as layout_state
from .editor import get_module_ui
from .payload import module_flow
from .scroll import viewport_head, viewport_tail
from .wrap import visible_wrap_lines


def resolve_label_input(ctx, binding_handle: str, spec: dict[str, Any]) -> str:
    from .. import registry

    attrs = dict(spec.get("attrs") or {})
    token = str(attrs.get("input") or "").strip()
    if not token:
        return str(binding_handle or registry.get_active_handle(ctx))
    if token == "|:handle":
        return str(binding_handle or registry.get_active_handle(ctx))
    if token.startswith("|:"):
        return str(layout_state.get_meta(ctx, binding_handle, token[2:], "") or "")
    if token.startswith("|") and token.count(":") == 1:
        owner, key = token.split(":", 1)
        owner_handle = registry.normalize_handle(owner)
        if key == "handle":
            return owner_handle
        meta = layout_state.get_meta(ctx, owner_handle, key, None)
        if meta is not None:
            return str(meta)
        return str(layout_state.get_value(ctx, token, "") or "")
    return str(layout_state.get_value(ctx, token, token) or "")


def render_monitor_lines(ctx, inst, spec: dict[str, Any], rect: dict[str, int]) -> list[str]:
    ui = get_module_ui(ctx, inst.handle)
    target = str(inst.view_target or inst.primary_target or "")
    value = layout_state.get_value(ctx, target, "")
    lines = str(value or "").splitlines() or [""]
    width = max(1, int(rect.get("w", 1) or 1))
    height = max(1, int(rect.get("h", 1) or 1))
    flow = module_flow(getattr(inst, "MODULE", ""), spec.get("attrs") or {})
    follow = bool(ui.get("follow", True))
    if follow:
        if flow == "top":
            return visible_wrap_lines(lines, width, height, "top")
        ui["scroll"] = 0
        return visible_wrap_lines(lines, width, height, "bottom")
    scroll = max(0, int(ui.get("scroll", 0) or 0))
    if flow == "top":
        visible = visible_wrap_lines(lines, width, max(1, scroll + height), "top")
        return visible[scroll : scroll + height] or [""]
    visible = visible_wrap_lines(lines, width, height + scroll, "bottom")
    if scroll > 0:
        visible = visible[:-scroll] if scroll < len(visible) else [""]
    return visible[-height:] or [""]


def _sorted_keys(value: dict[str, Any]) -> list[Any]:
    def sort_key(item: Any):
        text = str(item)
        return (0, int(text)) if text.isdigit() else (1, text)
    return sorted(value.keys(), key=sort_key)


def render_list_lines(ctx, inst) -> list[str]:
    value = layout_state.get_value(ctx, inst.primary_target, None)
    if isinstance(value, dict):
        keys = _sorted_keys(value)
        selected = int(get_module_ui(ctx, inst.handle).get("selected", 0) or 0)
        out: list[str] = []
        for i, key in enumerate(keys):
            prefix = "> " if i == selected else "  "
            out.append(f"{prefix}{key}: {value.get(key)}")
        return out or [""]
    if isinstance(value, list):
        selected = int(get_module_ui(ctx, inst.handle).get("selected", 0) or 0)
        out: list[str] = []
        for i, item in enumerate(value):
            prefix = "> " if i == selected else "  "
            out.append(f"{prefix}{item}")
        return out or [""]
    return str(value or "").splitlines() or [""]


def render_editor_lines(ctx, inst) -> list[str]:
    value = layout_state.get_value(ctx, inst.primary_target, "")
    return str(value or "").splitlines() or [""]


__all__ = [
    "resolve_label_input",
    "render_monitor_lines",
    "render_list_lines",
    "render_editor_lines",
]
