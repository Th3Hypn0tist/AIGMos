from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from system.lib.q.roles import resolve_role_value

from .lib.io import state_delete

from . import definitions
from . import loader as module_loader
from . import state as layout_state
from . import store as layout_store
from .lib.handles import (
    normalize_handle,
    route_name as _route_name,
    layout_handle_from_route as _layout_handle_from_route,
    binding_name as _binding_name,
    instance_suffix as _instance_suffix,
    instance_handle as _base_instance_handle,
)
from .lib.targets import primary_targets_for as _primary_target_for


@dataclass
class LayoutInstance:
    handle: str
    MODULE: str
    parent_layout: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    primary_target: str = ""
    view_target: str = ""
    title: str = ""
    prompt: str = "cs> "

    def get_title(self) -> str:
        return str(self.title or self.handle)

    def get_prompt(self) -> str:
        return str(self.prompt or "cs> ")


_Q_ROLE_RUNTIME_KEYS = (
    'name',
    'system_prompt',
    'view_thinking',
    'temperature',
    'top_k',
    'top_p',
    'repeat_penalty',
    'think',
    'stream',
)


def _q_role_symbol(base: str, key: str) -> str:
    return f"{str(base or '').strip()}:role:{str(key or '').strip()}"


def _clear_q_role_runtime(ctx, base: str) -> None:
    state = ctx.get('state') if isinstance(ctx, dict) else None
    if state is None:
        return
    legacy = (
        f"{base}:role",
        f"{base}:system_prompt",
        f"{base}:temperature",
        f"{base}:top_k",
        f"{base}:top_p",
        f"{base}:repeat_penalty",
        f"{base}:think",
        f"{base}:stream",
    )
    for symbol in legacy:
        try:
            state_delete(state, symbol, writer='layout:state', op='layout_delete_legacy_q_role')
        except Exception:
            pass
    for key in _Q_ROLE_RUNTIME_KEYS:
        try:
            state_delete(state, _q_role_symbol(base, key), writer='layout:state', op='layout_delete_q_role')
        except Exception:
            pass


def _runtime(ctx) -> dict[str, Any]:
    runtime = ctx.setdefault("layout_runtime", {})
    runtime.setdefault("bootstrapped", False)
    runtime.setdefault("bindings", {})
    runtime.setdefault("instances", {})
    runtime.setdefault("active_handle", "")
    runtime.setdefault("saved_instances", {})
    runtime.setdefault("_restoring_store", False)
    runtime.setdefault("_persist_suspended", 0)
    return runtime


def _module_prompt(module_name: str) -> str:
    return str(module_loader.module_meta(module_name)["default_prompt"])


def _instance_handle(binding_handle: str, spec_or_tag: Any, ordinal: int | None = None) -> str:
    if isinstance(spec_or_tag, dict):
        tag = str(spec_or_tag.get("tag") or "").strip().lower()
        module_id = str(spec_or_tag.get("module_id") or "").strip()
        index = int(spec_or_tag.get("ordinal") or ordinal or 1)
    else:
        tag = str(spec_or_tag or "").strip().lower()
        module_id = ""
        index = int(ordinal or 1)
    module_ref = module_id or _instance_suffix(binding_handle, tag, index)
    return _base_instance_handle(binding_handle, module_ref)


def _default_startup_layout_handle() -> str:
    return "|CS"


def load_module(ctx, module_name: str):
    return module_loader.load_module(module_name)


def _write_meta_for_instance(ctx, instance: LayoutInstance) -> None:
    layout_state.set_meta(ctx, instance.handle, "module", instance.MODULE)
    layout_state.set_meta(ctx, instance.handle, "title", instance.get_title())
    layout_state.set_meta(ctx, instance.handle, "prompt", instance.get_prompt())
    layout_state.set_meta(ctx, instance.handle, "status", "ok")
    layout_state.set_meta(ctx, instance.handle, "view_target", instance.view_target)
    layout_state.set_meta(ctx, instance.handle, "bound_module_name", instance.config.get("bound_module_name", ""))
    for key in ("parent_layout", "layout_name", "instance_suffix", "module_id", "target", "input", "source_handle", "runtime_root", "profile"):
        value = instance.config.get(key, "")
        layout_state.set_meta(ctx, instance.handle, key, "" if value is None else value)


def _apply_q_role_config(ctx, instance: LayoutInstance) -> None:
    state = ctx.get('state') if isinstance(ctx, dict) else None
    if state is None:
        return
    role_name = str(instance.config.get('role') or '').strip()
    base = str(instance.primary_target or '').strip()
    if not base:
        return

    _clear_q_role_runtime(ctx, base)

    if not role_name:
        layout_state.set_meta(ctx, instance.handle, 'role', '')
        return

    resolved = resolve_role_value(state, role_name)
    normalized_role = str(resolved.get('role') or role_name).strip()
    layout_state.set_value(ctx, _q_role_symbol(base, 'name'), normalized_role)
    layout_state.set_meta(ctx, instance.handle, 'role', normalized_role)

    if str(resolved.get('kind') or '') != 'preset':
        layout_state.set_value(ctx, _q_role_symbol(base, 'system_prompt'), '')
        layout_state.set_value(ctx, f"{base}:error", f"role preset not found: {role_name}")
        return

    system_prompt = str(resolved.get('system_prompt') or '')
    layout_state.set_value(ctx, _q_role_symbol(base, 'system_prompt'), system_prompt)
    layout_state.set_value(ctx, f"{base}:error", '')

    preset = dict(resolved.get('preset') or {})
    overrides = dict(resolved.get('profile_overrides') or {})

    view_thinking = preset.get('view_thinking', '')
    layout_state.set_value(ctx, _q_role_symbol(base, 'view_thinking'), True if view_thinking in (None, '') else view_thinking)

    for key in ('temperature', 'top_k', 'top_p', 'repeat_penalty', 'think', 'stream'):
        value = overrides.get(key, '')
        layout_state.set_value(ctx, _q_role_symbol(base, key), '' if value is None else value)


def _delete_instance_symbols(ctx, handle: str) -> None:
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if state is None:
        return
    try:
        inst = get_instance(ctx, handle)
    except Exception:
        inst = None
    prefixes = [normalize_handle(handle)]
    if inst is not None:
        primary = str(getattr(inst, "primary_target", "") or "").strip()
        if primary:
            prefixes.append(primary)
    layout_store.delete_layout_symbols(state, prefixes)


def create_instance(ctx, module_name: str, handle: str, config: dict[str, Any] | None = None, start: bool = True, restore: bool = False):
    from .persistence import _persist_runtime

    runtime = _runtime(ctx)
    clean_handle = normalize_handle(handle)
    config = dict(config or {})
    primary_target, view_target = _primary_target_for(module_name, clean_handle, config)
    instance = LayoutInstance(
        handle=clean_handle,
        MODULE=str(module_name or "").strip().lower(),
        parent_layout=str(config.get("parent_layout") or "").strip(),
        config=config,
        primary_target=primary_target,
        view_target=view_target,
        title=clean_handle,
        prompt=_module_prompt(module_name),
    )
    runtime["instances"][clean_handle] = instance
    if instance.MODULE == "q":
        if not restore:
            _clear_q_role_runtime(ctx, primary_target)
        defaults = {
            f"{primary_target}:ch": {},
            f"{primary_target}:response": "",
            f"{primary_target}:thinking_text": "",
            f"{primary_target}:prompt": "",
            f"{primary_target}:error": "",
            f"{primary_target}:role:name": "",
            f"{primary_target}:role:system_prompt": "",
            f"{primary_target}:role:view_thinking": True,
            f"{primary_target}:role:temperature": "",
            f"{primary_target}:role:top_k": "",
            f"{primary_target}:role:top_p": "",
            f"{primary_target}:role:repeat_penalty": "",
            f"{primary_target}:role:think": "",
            f"{primary_target}:role:stream": "",
        }
        for symbol, default_value in defaults.items():
            if layout_state.get_value(ctx, symbol, None) is None:
                layout_state.set_value(ctx, symbol, default_value)
        if not restore:
            _apply_q_role_config(ctx, instance)
    else:
        if layout_state.get_value(ctx, primary_target, None) is None:
            layout_state.set_value(ctx, primary_target, "")
    _write_meta_for_instance(ctx, instance)
    _persist_runtime(ctx)
    return instance


def has_instance(ctx, handle: str) -> bool:
    return normalize_handle(handle) in _runtime(ctx)["instances"]


def get_instance(ctx, handle: str):
    from .bindings import has_layout_binding

    runtime = _runtime(ctx)
    clean = normalize_handle(handle)
    inst = runtime["instances"].get(clean)
    if inst is not None:
        return inst
    if clean in runtime["bindings"]:
        binding = runtime["bindings"][clean]
        target = str(binding.get("input_module") or binding.get("active_module") or "")
        if target and target in runtime["instances"]:
            return runtime["instances"][target]
    if has_layout_binding(ctx, clean):
        binding = runtime["bindings"].get(clean)
        target = str((binding or {}).get("input_module") or (binding or {}).get("active_module") or "")
        if target and target in runtime["instances"]:
            return runtime["instances"][target]
    raise ValueError(f"layout not found: {handle}")


def list_instances(ctx) -> list[str]:
    runtime = _runtime(ctx)
    return sorted(runtime["instances"].keys(), key=lambda item: item[1:])


def ensure_instance(ctx, target: str):
    from .bindings import _ensure_layout_binding_runtime, create_layout_binding
    from .focus import bootstrap

    bootstrap(ctx)
    runtime = _runtime(ctx)
    text = str(target or "").strip()
    if not text:
        raise ValueError("layout target cannot be empty")

    if text.startswith("|"):
        clean = normalize_handle(text)
        if clean in runtime["bindings"]:
            _ensure_layout_binding_runtime(ctx, clean)
            return clean
        if clean in runtime["instances"]:
            return runtime["instances"][clean]
        raise ValueError(f"layout not found: {text}")

    if not text.startswith("/"):
        raise ValueError("layout route must start with /")

    route = _route_name(text)
    base = route.split(".", 1)[0].lower()

    try:
        tree = definitions.parse_layout_definition(base)
        handle = _layout_handle_from_route(text)
        if handle not in runtime["bindings"]:
            specs = definitions.flatten_module_specs(tree)
            create_layout_binding(ctx, handle, base, specs, tree=tree)
        _ensure_layout_binding_runtime(ctx, handle)
        return handle
    except Exception:
        pass

    module_name = base
    handle = _layout_handle_from_route(text)
    if handle not in runtime["instances"]:
        create_instance(ctx, module_name, handle, {}, start=True)
    return runtime["instances"][handle]


def save_instance(ctx, handle: str) -> None:
    runtime = _runtime(ctx)
    clean = normalize_handle(handle)
    runtime.setdefault("saved_instances", {})[clean] = True


def remove_instance(ctx, target: str) -> bool:
    from .persistence import _persist_runtime

    runtime = _runtime(ctx)
    clean = normalize_handle(target)
    state = ctx.get("state") if isinstance(ctx, dict) else None
    if clean in runtime["bindings"]:
        binding = runtime["bindings"].pop(clean)
        child_instances = {}
        for child in list(binding.get("modules") or []):
            child_instances[child] = runtime["instances"].pop(child, None)
        if runtime.get("active_handle") == clean:
            runtime["active_handle"] = _default_startup_layout_handle()
        if state is not None:
            prefixes = [clean]
            for child, inst in child_instances.items():
                prefixes.append(child)
                primary = str(getattr(inst, "primary_target", "") or "").strip() if inst is not None else ""
                if primary:
                    prefixes.append(primary)
            layout_store.delete_layout_symbols(state, prefixes)
        _persist_runtime(ctx)
        return True
    if clean in runtime["instances"]:
        inst = runtime["instances"].pop(clean)
        parent = inst.parent_layout
        if parent and parent in runtime["bindings"]:
            binding = runtime["bindings"][parent]
            binding["modules"] = [item for item in binding.get("modules") or [] if item != clean]
            if binding.get("active_module") == clean:
                binding["active_module"] = binding["modules"][0] if binding["modules"] else ""
        if runtime.get("active_handle") == clean:
            runtime["active_handle"] = parent or _default_startup_layout_handle()
        if state is not None:
            prefixes = [clean]
            primary = str(getattr(inst, "primary_target", "") or "").strip()
            if primary:
                prefixes.append(primary)
            layout_store.delete_layout_symbols(state, prefixes)
        _persist_runtime(ctx)
        return True
    return False


def clear_layout_modules(ctx, handle: str | None = None) -> list[str]:
    from .bindings import get_bound_layout_modules
    from .focus import bootstrap, get_active_handle

    bootstrap(ctx)
    owner = normalize_handle(handle or get_active_handle(ctx))
    runtime = _runtime(ctx)

    targets: list[str] = []
    if owner in runtime.get("bindings", {}):
        targets.extend(get_bound_layout_modules(ctx, owner))
    elif owner in runtime.get("instances", {}):
        targets.append(owner)
    else:
        raise ValueError(f"layout not found: {owner}")

    cleared: list[str] = []
    for module_handle in targets:
        try:
            inst = get_instance(ctx, module_handle)
        except Exception:
            continue
        try:
            module = load_module(ctx, getattr(inst, "MODULE", ""))
        except Exception:
            continue
        clear_fn = getattr(module, "clear", None)
        if callable(clear_fn):
            clear_fn(ctx, module_handle, inst)
            cleared.append(module_handle)

    parser = ctx.get("parser") if isinstance(ctx, dict) else None
    if parser is not None:
        from system.cs.runtime_ctx import force_render

        force_render(parser)
    return cleared
