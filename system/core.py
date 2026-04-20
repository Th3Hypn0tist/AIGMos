from __future__ import annotations

from typing import Any

import system.layout as layout


def _try_call(obj: Any, name: str) -> None:
    fn = getattr(obj, name, None)
    if callable(fn):
        try:
            fn()
        except Exception:
            pass


def _try_join(obj: Any, timeout: float = 1.0) -> None:
    fn = getattr(obj, "join", None)
    if callable(fn):
        try:
            fn(timeout=timeout)
        except Exception:
            pass


def _shutdown_ctx(ctx) -> None:
    flags = ctx.get("flags")
    if isinstance(flags, dict):
        flags["running"] = False
        flags["force_render"] = True

    for key in ("osc_server", "trigger_loop", "event_loop"):
        obj = ctx.get(key)
        if obj is None:
            continue
        _try_call(obj, "stop")
        _try_call(obj, "close")

    for key in ("osc_server", "trigger_loop", "event_loop"):
        obj = ctx.get(key)
        if obj is None:
            continue
        _try_join(obj, timeout=1.0)

    parser = ctx.get("parser")
    if parser is not None:
        try:
            from system.lib.q.live import shutdown_live_chat
            shutdown_live_chat(parser, timeout=1.5)
        except Exception:
            pass

    state = ctx.get("state")
    _try_call(state, "close")


def run(ctx) -> None:
    flags = ctx.setdefault("flags", {})
    flags.setdefault("running", True)
    flags.setdefault("force_render", True)

    try:
        layout.run_loop(ctx)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown_ctx(ctx)
