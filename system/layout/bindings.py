from __future__ import annotations

from typing import Any

from . import definitions
from . import state as layout_state
from .lib.handles import (
    normalize_handle,
    route_name as _route_name,
    instance_suffix as _instance_suffix,
)
from .instances import _runtime, _instance_handle, create_instance
from .lib.spec import config_for_spec, layout_title_from_tree

_IGNORE_BOUND_TAGS = {"label"}



def _binding_meta_write(ctx, handle: str, route_name: str, modules: list[str], active_module: str, *, input_module: str = "", q_module: str = "", tree: dict[str, Any] | None = None) -> None:
    layout_state.set_meta(ctx, handle, "layout_name", _route_name(route_name))
    layout_state.set_meta(ctx, handle, "title", layout_title_from_tree(tree, handle))
    layout_state.set_meta(ctx, handle, "status", "ok")
    layout_state.set_meta(ctx, handle, "view_target", f"{handle}:buffer")
    layout_state.set_meta(ctx, handle, "active_module", active_module)
    layout_state.set_meta(ctx, handle, "input_module", input_module)
    layout_state.set_meta(ctx, handle, "q_module", q_module)
    layout_state.set_value(ctx, f"{handle}:buffer", layout_state.get_value(ctx, f"{handle}:buffer", "") or "")
    current_history = layout_state.get_value(ctx, f"{handle}:command_history", None)
    if current_history is None:
        layout_state.set_value(ctx, f"{handle}:command_history", {})
    layout_state.set_meta(ctx, handle, "modules", list(modules))


def create_layout_binding(ctx, handle: str, route_name: str, specs: list[dict[str, Any]], tree: dict[str, Any] | None = None, restore: bool = False):
    from .persistence import _persist_runtime

    runtime = _runtime(ctx)
    binding_handle = normalize_handle(handle)
    binding = runtime["bindings"].get(binding_handle)
    if binding is None:
        binding = {
            "handle": binding_handle,
            "route_name": _route_name(route_name),
            "tree": tree,
            "specs": list(specs),
            "modules": [],
            "active_module": "",
        }
        runtime["bindings"][binding_handle] = binding
    else:
        binding["route_name"] = _route_name(route_name)
        binding["tree"] = tree
        binding["specs"] = list(specs)
        binding["modules"] = []
        binding["active_module"] = ""

    modules: list[str] = []
    cs_candidate = ""
    q_candidate = ""
    runtime["_persist_suspended"] = int(runtime.get("_persist_suspended") or 0) + 1
    try:
        for spec in specs:
            tag = str(spec.get("tag") or "").strip().lower()
            if tag in _IGNORE_BOUND_TAGS:
                continue
            child_handle = _instance_handle(binding_handle, spec)
            config = config_for_spec(binding_handle, _route_name(route_name), spec)
            config["parent_layout"] = binding_handle
            instance = create_instance(ctx, tag, child_handle, config, start=True, restore=restore)
            modules.append(instance.handle)
            if tag == "cs" and not cs_candidate:
                cs_candidate = instance.handle
            if tag == "q" and not q_candidate:
                q_candidate = instance.handle
    finally:
        runtime["_persist_suspended"] = max(0, int(runtime.get("_persist_suspended") or 0) - 1)

    input_module = cs_candidate or q_candidate or (modules[0] if modules else "")
    q_module = q_candidate or ""
    render_module = next((h for h in modules if getattr(_runtime(ctx)["instances"].get(h), "MODULE", "") in {"monitor", "qmon", "q"}), "") or input_module
    binding["modules"] = modules
    binding["active_module"] = render_module
    binding["input_module"] = input_module
    binding["q_module"] = q_module
    _binding_meta_write(ctx, binding_handle, route_name, modules, render_module, input_module=input_module, q_module=q_module, tree=binding.get('tree'))
    _persist_runtime(ctx)
    return modules


def _ensure_layout_binding_runtime(ctx, handle: str):
    runtime = _runtime(ctx)
    binding_handle = normalize_handle(handle)
    binding = runtime["bindings"].get(binding_handle)
    if binding is None:
        raise ValueError(f"layout not found: {binding_handle}")

    modules = []
    for spec in binding.get("specs") or []:
        tag = str(spec.get("tag") or "").strip().lower()
        if tag in _IGNORE_BOUND_TAGS:
            continue
        child_handle = _instance_handle(binding_handle, spec)
        config = config_for_spec(binding_handle, _route_name(binding.get('route_name') or binding_handle), spec)
        config["parent_layout"] = binding_handle
        if child_handle not in runtime["instances"]:
            create_instance(ctx, tag, child_handle, config, start=True)
        else:
            inst = runtime["instances"][child_handle]
            inst.config.update(config)
        modules.append(child_handle)

    binding["modules"] = modules
    instances = _runtime(ctx)["instances"]
    if binding.get("input_module") not in modules:
        binding["input_module"] = next((h for h in modules if getattr(instances.get(h), "MODULE", "") == "cs"), "") or next((h for h in modules if getattr(instances.get(h), "MODULE", "") == "q"), "") or (modules[0] if modules else "")
    if binding.get("q_module") not in modules:
        binding["q_module"] = next((h for h in modules if getattr(instances.get(h), "MODULE", "") == "q"), "")
    if binding.get("active_module") not in modules:
        binding["active_module"] = next((h for h in modules if getattr(instances.get(h), "MODULE", "") in {"monitor", "qmon", "q"}), "") or binding.get("input_module") or (modules[0] if modules else "")
    _binding_meta_write(ctx, binding_handle, binding.get('route_name') or binding_handle, modules, binding.get('active_module') or '', input_module=binding.get('input_module') or '', q_module=binding.get('q_module') or '', tree=binding.get('tree'))
    return modules


def has_layout_binding(ctx, handle: str) -> bool:
    return normalize_handle(handle) in _runtime(ctx)["bindings"]


def get_bound_layout_modules(ctx, handle: str) -> list[str]:
    binding = _runtime(ctx)["bindings"].get(normalize_handle(handle))
    if binding is None:
        raise ValueError("layout not found")
    _ensure_layout_binding_runtime(ctx, handle)
    return list(binding.get("modules") or [])


def get_bound_layout_active_module(ctx, handle: str) -> str:
    binding = _runtime(ctx)["bindings"].get(normalize_handle(handle))
    if binding is None:
        return ""
    _ensure_layout_binding_runtime(ctx, handle)
    return str(binding.get("active_module") or "")


def get_parent_layout_for_instance(ctx, handle: str) -> str:
    inst = _runtime(ctx)["instances"].get(normalize_handle(handle))
    return str(inst.parent_layout or "") if inst is not None else ""


def get_bound_layout_input_module(ctx, handle: str) -> str:
    binding = _runtime(ctx)["bindings"].get(normalize_handle(handle))
    if binding is None:
        return ""
    _ensure_layout_binding_runtime(ctx, handle)
    return str(binding.get("input_module") or "")


def get_bound_layout_q_module(ctx, handle: str) -> str:
    binding = _runtime(ctx)["bindings"].get(normalize_handle(handle))
    if binding is None:
        return ""
    _ensure_layout_binding_runtime(ctx, handle)
    return str(binding.get("q_module") or "")
