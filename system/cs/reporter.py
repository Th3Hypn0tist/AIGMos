# system/cs/reporter.py
from __future__ import annotations

import threading
from datetime import datetime

from system.cs.runtime_ctx import force_render, get_ctx, get_layout_caller_handle, get_runtime
from system.state.api import append_numeric_value, read_value, write_value


def _parser_writer_tag(parser, default_writer: str = "parser:unknown") -> str:
    runtime = getattr(parser, "runtime", {}) or {}
    value = str(runtime.get("_active_writer_tag") or "").strip()
    return value or default_writer


def resolve_buffer_target(parser) -> str:
    caller_handle = get_layout_caller_handle(parser)
    explicit_handle = str(get_runtime(parser, "buffer_handle", "") or "").strip()

    ctx = get_ctx(parser)
    candidates: list[str] = [caller_handle, explicit_handle]

    try:
        from system.layout import registry as layout_registry  # type: ignore
        from system.layout import state as layout_state  # type: ignore

        layout_registry.bootstrap(ctx)
        active_handle = str(layout_state.get_active_handle(ctx, "|CS") or "|CS").strip()
        if active_handle:
            candidates.append(active_handle)
            if layout_registry.has_layout_binding(ctx, active_handle):
                child = layout_registry.get_bound_layout_active_module(ctx, active_handle)
                if child:
                    candidates.append(child)
        candidates.append("|CS")

        seen = set()
        for handle in candidates:
            clean = str(handle or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            try:
                if layout_registry.has_instance(ctx, clean):
                    return layout_registry.get_layout_buffer_target(ctx, clean)
                if layout_registry.has_layout_binding(ctx, clean):
                    return f"{clean}:buffer"
            except Exception:
                continue
    except Exception:
        pass

    return "|CS:buffer"


def write_buffer(parser, message: str) -> None:
    if get_runtime(parser, "buffer_suppress", False):
        force_render(parser)
        return

    pushed_live = False

    try:
        ui_thread_id = get_runtime(parser, "ui_thread_id", None)
        live_push = get_runtime(parser, "buffer_live_push", None)

        if (
            ui_thread_id is not None
            and threading.get_ident() != ui_thread_id
            and callable(live_push)
        ):
            live_push(message)
            pushed_live = True
    except Exception:
        pushed_live = False

    try:
        target = resolve_buffer_target(parser)
        result = append_numeric_value(
            parser.state,
            target,
            message,
            writer=_parser_writer_tag(parser, "parser:buffer"),
            op="buffer_append",
        )
        if result.get("error"):
            force_render(parser)
            return

        force_render(parser)

    except Exception:
        force_render(parser)
        return

    if pushed_live:
        return


def write_error_log(parser, full_command: str, errormsg: str) -> None:
    try:
        current = read_value(parser.state, "$SYSTEM.ERRORS", {}) or {}
        if not isinstance(current, dict):
            current = {}

        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        key = ts
        while key in current:
            key = str(int(key) + 1)

        current[key] = f"{full_command};{errormsg}"

        result = write_value(
            parser.state,
            "$SYSTEM.ERRORS",
            current,
            writer=_parser_writer_tag(parser, "parser:error"),
            op="error_log",
        )
        if result["error"]:
            return

    except Exception:
        return


def handle_error(parser, full_command: str, errormsg: str) -> str:
    try:
        write_error_log(parser, full_command, errormsg)
    except Exception:
        pass

    try:
        write_buffer(parser, f"[error] {errormsg}")
    except Exception:
        pass

    return errormsg
