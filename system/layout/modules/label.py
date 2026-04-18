from __future__ import annotations

from typing import Any

from system.layout.lib.border import content_rect
from system.layout.lib.payload import finalize_payload
from system.layout.lib.view_resolvers import resolve_label_input
from system.layout.lib.wrap import wrap_text

MODULE = "label"
DEFAULT_PROMPT = ""
FOCUSABLE = False


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    return f"{handle}:buffer", f"{handle}:buffer"


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    text = resolve_label_input(ctx, binding_handle, spec)
    return {"min_h": max(1, len(wrap_text(text, width))), "scalable_y": False}


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    text = resolve_label_input(ctx, binding_handle, spec)
    module_handle = getattr(instance, "handle", None) or f"{binding_handle}:label:{id(spec)}"
    inner_rect = content_rect(attrs, rect)
    return finalize_payload(ctx, str(module_handle), wrap_text(text, max(1, inner_rect.get("w", 1))), attrs, MODULE, rect)
