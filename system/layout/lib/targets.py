from __future__ import annotations

from typing import Any

from .. import loader as module_loader
from .handles import normalize_handle, state_root_for_handle, state_root_for_target


def layout_buffer_target(handle: str) -> str:
    return f"{str(handle or '').strip()}:buffer"


def _binding_root(handle: str) -> str:
    clean = normalize_handle(handle)
    return clean.split(':', 1)[0]


def resolve_querytarget(raw_target: str, current_handle: str = '') -> str:
    raw = str(raw_target or '').strip()
    if not raw:
        raise ValueError('querytarget cannot be empty')
    if not raw.startswith('|'):
        raise ValueError('querytarget must start with |')
    if raw.startswith('|:'):
        suffix = str(raw[2:] or '').strip()
        if not suffix:
            raise ValueError('relative querytarget requires module id')
        base = _binding_root(current_handle)
        return normalize_handle(f"{base}:{suffix}")
    return normalize_handle(raw)


def get_cs_qtarget(config: dict[str, Any] | None = None, *, current_handle: str = '') -> str:
    cfg = dict(config or {})
    raw = str(cfg.get('qtarget') or '').strip()
    if not raw:
        return ''
    context = str(cfg.get('parent_layout') or current_handle or '').strip()
    return resolve_querytarget(raw, context)


def q_targets_for_handle(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    cfg = dict(config or {})
    runtime_root = str(cfg.get('runtime_root') or cfg.get('state_handle') or handle or '').strip()
    base = state_root_for_handle(runtime_root)
    return base, f'{base}:ch'


def qmon_targets_for_source(config: dict[str, Any] | None = None) -> tuple[str, str]:
    cfg = dict(config or {})
    source_handle = str(cfg.get('source_handle') or cfg.get('target') or '').strip()
    if source_handle.startswith('|:'):
        source_handle = resolve_querytarget(source_handle, str(cfg.get('parent_layout') or '').strip())
    base = state_root_for_target(source_handle)
    if not base:
        raise ValueError('qmon requires explicit target')
    return base, f'{base}:ch'


def primary_targets_for(module_name: str, handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    module = module_loader.load_module(module_name)
    primary_target, view_target = module.get_targets(handle, dict(config or {}))
    return str(primary_target), str(view_target)


def get_layout_buffer_target(ctx, handle: str) -> str:
    from .. import registry

    clean = normalize_handle(handle)
    parent = registry.get_parent_layout_for_instance(ctx, clean)
    if parent:
        return layout_buffer_target(parent)
    if registry.has_layout_binding(ctx, clean):
        return layout_buffer_target(clean)
    return layout_buffer_target(clean)


def get_primary_target(ctx, handle: str) -> str:
    from .. import registry

    clean = normalize_handle(handle)
    if registry.has_layout_binding(ctx, clean):
        inst = registry.get_instance(ctx, clean)
        if getattr(inst, 'MODULE', '') == 'q':
            return str(inst.primary_target)
        return layout_buffer_target(clean)
    return str(registry.get_instance(ctx, clean).primary_target)
