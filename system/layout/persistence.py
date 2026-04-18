from __future__ import annotations

from typing import Any

from system.state.api import list_symbols

from . import definitions
from . import state as layout_state
from .bindings import create_layout_binding
from .focus import switch_active
from .instances import _runtime, _default_startup_layout_handle, create_instance, _write_meta_for_instance
from .lib.handles import normalize_handle, route_name as _route_name


def _active_handle_for_store(ctx) -> str:
    runtime = _runtime(ctx)
    active = str(runtime.get("active_handle") or "").strip()
    if active:
        return active
    persisted = layout_state.get_meta(ctx, "|LAYOUT", "active_handle", "")
    return str(persisted or "").strip()


def _layout_store_payload(ctx) -> dict[str, Any]:
    runtime = _runtime(ctx)
    return {
        "active_handle": _active_handle_for_store(ctx),
        "bindings": sorted(dict(runtime.get("bindings") or {}).keys()),
        "instances": sorted(dict(runtime.get("instances") or {}).keys()),
    }


def _persist_runtime(ctx) -> None:
    runtime = _runtime(ctx)
    active = str(runtime.get("active_handle") or "").strip()
    if active:
        layout_state.set_meta(ctx, "|LAYOUT", "active_handle", active)


def _binding_specs_from_store(route_name: str, item: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    try:
        parsed = definitions.parse_layout_definition(_route_name(route_name))
        return list(definitions.flatten_module_specs(parsed)), parsed
    except Exception:
        return [], None


def _top_level_handles_from_state(ctx) -> list[str]:
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if state is None:
        return []
    handles: set[str] = set()
    for symbol in list_symbols(state):
        if not symbol.startswith('|'):
            continue
        top = symbol.split(':', 1)[0].strip()
        if not top or top == '|LAYOUT':
            continue
        try:
            handles.add(normalize_handle(top))
        except Exception:
            continue
    return sorted(handles, key=lambda item: item[1:])


def _meta_value(ctx, handle: str, key: str, default: Any = "") -> Any:
    return layout_state.get_meta(ctx, handle, key, default)


def _state_role_name(ctx, runtime_root: str) -> str:
    clean = str(runtime_root or '').strip()
    if not clean:
        return ''
    value = layout_state.get_value(ctx, f"{clean}:role:name", "")
    return str(value or '').strip()


def _instance_config_from_state(ctx, handle: str, module_name: str, *, parent_layout: str = "") -> dict[str, Any]:
    clean = normalize_handle(handle)
    module = str(module_name or '').strip().lower()
    config: dict[str, Any] = {}

    for key in ("layout_name", "instance_suffix", "bound_module_name", "module_id", "target", "input", "source_handle", "runtime_root", "profile"):
        value = _meta_value(ctx, clean, key, "")
        if value not in (None, ""):
            config[key] = value

    if parent_layout:
        config["parent_layout"] = parent_layout
    else:
        parent_meta = str(_meta_value(ctx, clean, "parent_layout", "") or '').strip()
        if parent_meta:
            config["parent_layout"] = parent_meta

    if module == 'q':
        config.setdefault('runtime_root', clean)
        role_name = str(_meta_value(ctx, clean, 'role', '') or '').strip() or _state_role_name(ctx, str(config.get('runtime_root') or clean))
        if role_name:
            config['role'] = role_name
        profile = str(config.get('profile') or '').strip()
        if not profile:
            body = clean[1:]
            profile = 'default' if body.upper().startswith('Q') else 'default'
            config['profile'] = profile

    return config


def _restore_runtime_from_store(ctx) -> None:
    runtime = _runtime(ctx)
    runtime["bindings"] = {}
    runtime["instances"] = {}
    runtime["focus"] = {}

    runtime["_restoring_store"] = True
    runtime["_persist_suspended"] = int(runtime.get("_persist_suspended") or 0) + 1
    try:
        handles = _top_level_handles_from_state(ctx)
        for handle in handles:
            route_name = str(_meta_value(ctx, handle, 'layout_name', '') or '').strip()
            if not route_name:
                continue
            specs, tree = _binding_specs_from_store(route_name, None)
            if not specs:
                continue
            create_layout_binding(ctx, handle, route_name, specs, tree=tree, restore=True)

        for handle in handles:
            if handle in runtime.get('bindings', {}):
                continue
            if handle in runtime.get('instances', {}):
                inst = runtime['instances'][handle]
                title = str(_meta_value(ctx, handle, 'title', '') or '').strip()
                prompt = str(_meta_value(ctx, handle, 'prompt', '') or '').strip()
                if title:
                    inst.title = title
                if prompt:
                    inst.prompt = prompt
                _write_meta_for_instance(ctx, inst)
                continue
            module_name = str(_meta_value(ctx, handle, 'module', '') or '').strip().lower()
            if not module_name:
                continue
            config = _instance_config_from_state(ctx, handle, module_name)
            inst = create_instance(ctx, module_name, handle, config, start=True, restore=True)
            title = str(_meta_value(ctx, handle, 'title', '') or '').strip()
            prompt = str(_meta_value(ctx, handle, 'prompt', '') or '').strip()
            if title:
                inst.title = title
            if prompt:
                inst.prompt = prompt
            _write_meta_for_instance(ctx, inst)
    finally:
        runtime["_persist_suspended"] = max(0, int(runtime.get("_persist_suspended") or 0) - 1)
        runtime["_restoring_store"] = False

    active = str(layout_state.get_meta(ctx, "|LAYOUT", "active_handle", "") or "").strip()
    if active:
        try:
            runtime["active_handle"] = normalize_handle(active)
        except Exception:
            runtime["active_handle"] = ""


def reload_layout(ctx) -> list[str]:
    from .focus import bootstrap
    from .instances import ensure_instance

    runtime = _runtime(ctx)
    active = _active_handle_for_store(ctx) or _default_startup_layout_handle()
    runtime['bindings'] = {}
    runtime['instances'] = {}
    runtime['focus'] = {}
    runtime['bootstrapped'] = False
    if isinstance(ctx, dict):
        ctx['_layout_frame_cache'] = {}
        ctx['layout_ui'] = {'editors': {}, 'modules': {}}
        flags = ctx.setdefault('flags', {})
        flags['layout_dirty_modules'] = set()
        flags['layout_hard_redraw'] = True
        flags['force_render'] = True
    bootstrap(ctx)
    if active:
        try:
            ensure_instance(ctx, active)
            switch_active(ctx, active)
        except Exception:
            switch_active(ctx, _default_startup_layout_handle())
    return sorted([binding["route_name"] for binding in runtime["bindings"].values()])
