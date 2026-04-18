from __future__ import annotations

import threading

from system.cs.runtime_ctx import force_render, get_runtime, set_runtime
from system.cs.symbols import is_symbol_line
from system.state.api import append_numeric_value

from .focus import bootstrap, get_active_handle, switch_active
from .instances import ensure_instance, get_instance
from .bindings import has_layout_binding, get_bound_layout_input_module, get_bound_layout_q_module
from .lib.handles import normalize_handle
from .lib.targets import get_cs_qtarget, get_layout_buffer_target


def is_ui_instance_switch_line(line: str) -> bool:
    clean = str(line or "").strip()
    if not clean or not clean.startswith("|"):
        return False
    if ":" in clean:
        return False
    if any(ch.isspace() for ch in clean):
        return False
    if "=" in clean:
        return False
    try:
        normalize_handle(clean)
    except Exception:
        return False
    return True


def _append_command_to_buffer(ctx, line: str, *, source_handle: str | None = None) -> None:
    clean = str(line or "").rstrip("\r\n")
    if not clean.strip():
        return
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if state is None:
        return
    handle = normalize_handle(source_handle or get_active_handle(ctx))
    target = get_layout_buffer_target(ctx, handle)
    append_numeric_value(
        state,
        target,
        f"> {clean}",
        writer="layout:input",
        op="layout_command_echo",
    )


def _command_history_owner(ctx, source_handle: str | None = None) -> str:
    handle = normalize_handle(source_handle or get_active_handle(ctx))
    try:
        inst = get_instance(ctx, handle)
        parent_layout = str(getattr(inst, "parent_layout", "") or "").strip()
        if parent_layout:
            return normalize_handle(parent_layout)
    except Exception:
        pass
    return handle


def _append_command_to_history(ctx, line: str, *, source_handle: str | None = None) -> None:
    clean = str(line or "").rstrip("\r\n")
    if not clean.strip():
        return
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if state is None:
        return
    owner = _command_history_owner(ctx, source_handle=source_handle)
    append_numeric_value(
        state,
        f"{owner}:command_history",
        clean,
        writer="layout:input",
        op="layout_command_history",
    )


def _append_error_to_buffer(ctx, message: str, *, source_handle: str | None = None) -> None:
    clean = str(message or "").rstrip("\r\n")
    if not clean.strip():
        return
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if state is None:
        return
    try:
        handle = normalize_handle(source_handle or get_active_handle(ctx))
    except Exception:
        handle = "|CS"
    target = get_layout_buffer_target(ctx, handle)
    append_numeric_value(
        state,
        target,
        clean,
        writer="layout:input",
        op="layout_error_echo",
    )


def _parser_parse_with_layout(
    ctx,
    line: str,
    *,
    caller_handle: str | None = None,
    buffer_suppress: bool = False,
    layout_self_route: bool = False,
):
    parser = ctx.get("parser")
    if parser is None:
        raise ValueError("parser missing")

    effective_handle = normalize_handle(caller_handle or get_active_handle(ctx))
    q_state_root = ""
    try:
        lookup_handle = effective_handle
        if has_layout_binding(ctx, effective_handle):
            bound_q = str(get_bound_layout_q_module(ctx, effective_handle) or "").strip()
            if bound_q:
                lookup_handle = bound_q
            else:
                bound_input = str(get_bound_layout_input_module(ctx, effective_handle) or "").strip()
                if bound_input:
                    lookup_handle = bound_input
        inst = get_instance(ctx, lookup_handle)
        if getattr(inst, "MODULE", "") == "q":
            q_state_root = str(getattr(inst, "primary_target", "") or "").strip()
    except Exception:
        q_state_root = ""

    lock = getattr(parser, "_parse_lock", None)
    if lock is None:
        previous = get_runtime(parser, "layout_caller_handle", "")
        previous_suppress = get_runtime(parser, "buffer_suppress", False)
        previous_self_route = get_runtime(parser, "layout_self_route", False)
        previous_q_root = get_runtime(parser, "q_state_root", "")
        set_runtime(parser, "layout_caller_handle", effective_handle)
        set_runtime(parser, "buffer_suppress", bool(buffer_suppress))
        set_runtime(parser, "layout_self_route", bool(layout_self_route))
        set_runtime(parser, "q_state_root", q_state_root)
        try:
            return parser.parse(line)
        finally:
            set_runtime(parser, "layout_caller_handle", previous)
            set_runtime(parser, "buffer_suppress", previous_suppress)
            set_runtime(parser, "layout_self_route", previous_self_route)
            set_runtime(parser, "q_state_root", previous_q_root)

    with lock:
        previous = get_runtime(parser, "layout_caller_handle", "")
        previous_suppress = get_runtime(parser, "buffer_suppress", False)
        previous_self_route = get_runtime(parser, "layout_self_route", False)
        previous_q_root = get_runtime(parser, "q_state_root", "")
        set_runtime(parser, "layout_caller_handle", effective_handle)
        set_runtime(parser, "buffer_suppress", bool(buffer_suppress))
        set_runtime(parser, "layout_self_route", bool(layout_self_route))
        set_runtime(parser, "q_state_root", q_state_root)
        try:
            return parser.parse(line)
        finally:
            set_runtime(parser, "layout_caller_handle", previous)
            set_runtime(parser, "buffer_suppress", previous_suppress)
            set_runtime(parser, "layout_self_route", previous_self_route)
            set_runtime(parser, "q_state_root", previous_q_root)


def _line_routes_to_parser(ctx, line: str, *, query_bound: bool = False) -> bool:
    clean = str(line or "").strip()
    if not clean:
        return False
    if clean.startswith("/") or clean.startswith("|"):
        return True
    if is_symbol_line(clean):
        if query_bound and "=" not in clean:
            return False
        return True
    parser = ctx.get("parser")
    if parser is None:
        return False
    token = clean.split()[0]
    if token == "/":
        return True
    return token in getattr(parser, "registry", {})


def _dispatch_q_self_route_async(ctx, line: str, *, caller_handle: str | None = None) -> None:
    parser = ctx.get("parser") if isinstance(ctx, dict) else None
    if parser is None:
        return

    def _run() -> None:
        try:
            _parser_parse_with_layout(
                ctx,
                line,
                caller_handle=caller_handle,
                buffer_suppress=True,
                layout_self_route=True,
            )
        finally:
            force_render(parser)

    thread = threading.Thread(target=_run, name="layout-q-self-route", daemon=True)
    thread.start()


def dispatch_line(ctx, line: str, *, source_handle: str | None = None, target_handle: str | None = None) -> dict[str, str]:
    bootstrap(ctx)
    clean = str(line or "").rstrip("\r\n")
    if not clean.strip():
        return {"mode": "none"}

    if is_ui_instance_switch_line(clean):
        try:
            target = ensure_instance(ctx, clean)
            handle = str(getattr(target, "handle", target) or clean).strip() or clean
            switch_active(ctx, handle)
            return {"mode": "switch"}
        except Exception:
            _append_error_to_buffer(ctx, "[error] Invalid layout", source_handle=source_handle or get_active_handle(ctx))
            return {"mode": "error", "error": "Invalid layout"}

    caller_handle = normalize_handle(source_handle or get_active_handle(ctx))
    _append_command_to_history(ctx, clean, source_handle=caller_handle)
    effective_handle = normalize_handle(target_handle or caller_handle)
    resolved_handle = effective_handle
    query_target = ""

    try:
        if has_layout_binding(ctx, effective_handle):
            bound_input = str(get_bound_layout_input_module(ctx, effective_handle) or "").strip()
            if bound_input:
                resolved_handle = normalize_handle(bound_input)
    except Exception:
        resolved_handle = effective_handle

    try:
        input_inst = get_instance(ctx, resolved_handle)
        if getattr(input_inst, "MODULE", "") == "cs":
            query_target = get_cs_qtarget(getattr(input_inst, "config", {}), current_handle=effective_handle)
    except Exception:
        query_target = ""

    if _line_routes_to_parser(ctx, clean, query_bound=bool(query_target)):
        _append_command_to_buffer(ctx, clean, source_handle=caller_handle)
        _parser_parse_with_layout(ctx, clean, caller_handle=effective_handle)
        return {"mode": "parser"}

    if not query_target:
        return {"mode": "none"}

    try:
        inst = get_instance(ctx, query_target)
    except Exception:
        _append_error_to_buffer(ctx, "[error] Invalid querytarget", source_handle=caller_handle)
        return {"mode": "error", "error": "Invalid querytarget"}

    if getattr(inst, "MODULE", "") == "q":
        profile = str(inst.config.get("profile") or "default").strip() or "default"
        cmd = "q" if profile == "default" else f"q.{profile}"
        _dispatch_q_self_route_async(ctx, f"{cmd} {query_target} {clean}", caller_handle=effective_handle)
        return {"mode": "self"}

    _append_error_to_buffer(ctx, "[error] target is not query-capable", source_handle=caller_handle)
    return {"mode": "error", "error": "target is not query-capable"}
