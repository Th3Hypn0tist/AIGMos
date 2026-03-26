# system/core.py

from __future__ import annotations

from system.layout.render import render_layout, get_layout_module


def run(ctx: dict) -> None:
    flags = ctx["flags"]

    while flags["running"]:
        if flags["force_render"]:
            render_layout(ctx, force=True)
            flags["force_render"] = False

        layout = get_layout_module(ctx)

        try:
            command = layout.read_input(ctx)
        except (EOFError, KeyboardInterrupt):
            break

        layout.handle_input(ctx, command)
        flags["force_render"] = True
