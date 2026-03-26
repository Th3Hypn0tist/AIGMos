from __future__ import annotations

from system.layout import buffer as buffer_layout
from system.layout import q as q_layout


def get_layout_module(ctx):
    out = ctx["state"].get("$SYSTEM.LAYOUT")
    if out["error"] or not out["result"]:
        return buffer_layout

    mode_name = str(out["result"]).strip().lower()

    if mode_name == "q":
        return q_layout

    return buffer_layout


def render_layout(ctx, force: bool = False):
    layout = get_layout_module(ctx)
    return layout.render(ctx, force=force)
