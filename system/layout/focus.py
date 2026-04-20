from __future__ import annotations

from typing import Any

from system.cs.runtime_ctx import force_render

from . import definitions
from . import state as layout_state
from .bindings import _ensure_layout_binding_runtime, create_layout_binding, get_bound_layout_modules, get_parent_layout_for_instance, has_layout_binding
from .instances import _runtime, _default_startup_layout_handle, get_instance, load_module
from .lib.handles import normalize_handle


def _focus_runtime(ctx) -> dict[str, Any]:
    runtime = _runtime(ctx)
    return runtime.setdefault("focus", {})


def _ensure_startup_layout(ctx) -> None:
    runtime = _runtime(ctx)
    if "|CS" not in runtime["bindings"]:
        tree = definitions.parse_layout_definition("cs")
        specs = definitions.flatten_module_specs(tree)
        create_layout_binding(ctx, "|CS", "cs", specs, tree=tree)
    _ensure_layout_binding_runtime(ctx, "|CS")


def bootstrap(ctx) -> None:
    from .persistence import _restore_runtime_from_store

    runtime = _runtime(ctx)
    if runtime.get("bootstrapped"):
        _ensure_startup_layout(ctx)
        return
    runtime["bootstrapped"] = True
    _restore_runtime_from_store(ctx)
    _ensure_startup_layout(ctx)
    active = str(runtime.get("active_handle") or "").strip() or _default_startup_layout_handle()
    try:
        switch_active(ctx, active)
    except Exception:
        switch_active(ctx, _default_startup_layout_handle())


def get_focusable_module_handles(ctx, handle: str | None = None) -> list[str]:
    bootstrap(ctx)
    clean = normalize_handle(handle or get_active_handle(ctx))
    runtime = _runtime(ctx)
    if clean in runtime["bindings"]:
        modules = get_bound_layout_modules(ctx, clean)
    elif clean in runtime["instances"]:
        modules = [clean]
    else:
        return []

    focusable: list[str] = []
    for item in modules:
        try:
            inst = get_instance(ctx, item)
        except Exception:
            continue
        module = load_module(ctx, getattr(inst, "MODULE", ""))
        if bool(getattr(module, "FOCUSABLE", False)):
            focusable.append(inst.handle)
    return focusable


def get_focused_module_handle(ctx, handle: str | None = None) -> str:
    bootstrap(ctx)
    owner = normalize_handle(handle or get_active_handle(ctx))
    focus = _focus_runtime(ctx)
    current = str(focus.get(owner) or "")
    focusable = get_focusable_module_handles(ctx, owner)
    if current in focusable:
        return current
    if focusable:
        preferred = next((item for item in focusable if get_instance(ctx, item).MODULE == "cs"), focusable[0])
        focus[owner] = preferred
        return preferred
    if owner in _runtime(ctx)["instances"]:
        inst = get_instance(ctx, owner)
        module = load_module(ctx, getattr(inst, "MODULE", ""))
        if bool(getattr(module, "FOCUSABLE", False)):
            focus[owner] = owner
            return owner
    return ""


def set_focused_module_handle(ctx, module_handle: str) -> str:
    clean_module = normalize_handle(module_handle)
    owner = get_parent_layout_for_instance(ctx, clean_module) or clean_module
    _focus_runtime(ctx)[normalize_handle(owner)] = clean_module
    return clean_module


def cycle_focus(ctx, step: int = 1, handle: str | None = None) -> str:
    owner = normalize_handle(handle or get_active_handle(ctx))
    focusable = get_focusable_module_handles(ctx, owner)
    if not focusable:
        return ""
    current = get_focused_module_handle(ctx, owner)
    if current not in focusable:
        return set_focused_module_handle(ctx, focusable[0])
    pos = focusable.index(current)
    target = focusable[(pos + int(step)) % len(focusable)]
    return set_focused_module_handle(ctx, target)


def get_active_handle(ctx) -> str:
    return layout_state.get_active_handle(ctx, _default_startup_layout_handle())


def set_active_handle(ctx, handle: str) -> str:
    return layout_state.set_active_handle(ctx, normalize_handle(handle))


def switch_active(ctx, handle: str) -> str:
    from .persistence import _persist_runtime

    clean = normalize_handle(handle)
    runtime = _runtime(ctx)
    if clean not in runtime["bindings"] and clean not in runtime["instances"]:
        raise ValueError(f"layout not found: {handle}")
    set_active_handle(ctx, clean)
    get_focused_module_handle(ctx, clean)
    _persist_runtime(ctx)
    parser = ctx.get("parser") if isinstance(ctx, dict) else None
    if parser is not None:
        force_render(parser)
    return clean


def get_active_instance(ctx):
    return get_instance(ctx, get_active_handle(ctx))
