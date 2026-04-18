from __future__ import annotations

from system.layout.render import get_layout_module, render_layout


def shutdown(ctx: dict) -> None:
    trigger_loop = ctx.get("trigger_loop")
    event_loop = ctx.get("event_loop")
    osc_server = ctx.get("osc_server")

    for item in (trigger_loop, event_loop, osc_server):
        stop = getattr(item, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass

    for item in (trigger_loop, event_loop, osc_server):
        join = getattr(item, "join", None)
        if callable(join):
            try:
                join(timeout=0.5)
            except Exception:
                pass

    sqlite_adapter = ctx.get("sqlite_adapter")
    conn = getattr(sqlite_adapter, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def run(ctx: dict) -> None:
    flags = ctx["flags"]
    parser = ctx["parser"]

    try:
        while flags.get("running", False):
            if parser.should_exit:
                flags["running"] = False
                break

            if flags.get("force_render"):
                render_layout(ctx, force=True)
                flags["force_render"] = False

            layout = get_layout_module(ctx)

            try:
                command = layout.read_input(ctx)
            except (EOFError, KeyboardInterrupt):
                flags["running"] = False
                break

            layout.handle_input(ctx, command)
            if parser.should_exit:
                flags["running"] = False
                break
            flags["force_render"] = True
    finally:
        shutdown(ctx)
