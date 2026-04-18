from __future__ import annotations

from system.layout.modules import buffer as buffer_layout
from system.layout.modules import q as q_layout


DEFAULT_LAYOUT = "buffer"

_LAYOUTS = {
    "buffer": buffer_layout,
    "q": q_layout,
}


def get_layout_name(ctx) -> str:
    out = ctx["state"].get("$SYSTEM.LAYOUT")
    if out["error"] or not out["result"]:
        return DEFAULT_LAYOUT
    return str(out["result"]).strip().lower() or DEFAULT_LAYOUT


def get_layout_module(ctx):
    return _LAYOUTS.get(get_layout_name(ctx), buffer_layout)


def render(ctx, force: bool = False):
    return get_layout_module(ctx).render(ctx, force=force)


def render_layout(ctx, force: bool = False):
    return render(ctx, force=force)


def read_input(ctx) -> str:
    return get_layout_module(ctx).read_input(ctx)


def handle_input(ctx, command: str) -> None:
    get_layout_module(ctx).handle_input(ctx, command)


def push_live_line(ctx, text: str) -> None:
    module = get_layout_module(ctx)
    handler = getattr(module, "push_live_line", None)
    if callable(handler):
        handler(ctx, text)
        return
    print(text, flush=True)
