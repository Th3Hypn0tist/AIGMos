from __future__ import annotations

from typing import Any

from system.cs.runtime_ctx import force_render
from system.state.api import delete_value, read_value, write_value


def meta_prefix(handle: str) -> str:
    return f"{str(handle or '').strip()}:meta"


def state_get(state, symbol: str, default: Any = None) -> Any:
    return read_value(state, symbol, default)


def state_set(state, symbol: str, value: Any, *, writer: str = 'layout:io', op: str = 'layout_set') -> None:
    out = write_value(state, symbol, value, writer=writer, op=op)
    if out.get('error'):
        raise ValueError(str(out['error']))


def state_delete(state, symbol: str, *, writer: str = 'layout:io', op: str = 'layout_delete') -> None:
    out = delete_value(state, symbol, writer=writer, op=op)
    if out.get('error'):
        raise ValueError(str(out['error']))


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def get_value(ctx, symbol: str, default: Any = None) -> Any:
    state = ctx.get('state') if isinstance(ctx, dict) else None
    if state is None:
        return default
    frame = ctx.get('_layout_frame_cache') if isinstance(ctx, dict) else None
    key = str(symbol)
    if isinstance(frame, dict) and key in frame:
        value = frame[key]
        return default if value is None else value
    value = state_get(state, symbol, default)
    if isinstance(frame, dict):
        frame[key] = value
    return default if value is None else value


def set_value(ctx, symbol: str, value: Any) -> None:
    state = ctx.get('state') if isinstance(ctx, dict) else None
    if state is None:
        return
    state_set(state, symbol, value, writer='layout:state', op='layout_set')


def get_meta(ctx, handle: str, key: str, default: Any = None) -> Any:
    return get_value(ctx, f"{meta_prefix(handle)}:{key}", default)


def set_meta(ctx, handle: str, key: str, value: Any) -> None:
    set_value(ctx, f"{meta_prefix(handle)}:{key}", value)


def set_title(ctx, handle: str, value: str) -> None:
    set_meta(ctx, handle, 'title', str(value or ''))


def set_prompt(ctx, handle: str, value: str) -> None:
    set_meta(ctx, handle, 'prompt', str(value or ''))


def set_view_material(ctx, handle: str, value: Any) -> None:
    set_meta(ctx, handle, 'material', value)


def refresh_instance_material(ctx, handle: str, redraw_if_active: bool = False) -> None:
    if not redraw_if_active:
        return
    parser = ctx.get('parser') if isinstance(ctx, dict) else None
    if parser is not None:
        force_render(parser)


def get_active_handle(ctx, default: str = '|CS') -> str:
    runtime = ctx.setdefault('layout_runtime', {}) if isinstance(ctx, dict) else {}
    clean = str(runtime.get('active_handle') or '').strip()
    return clean or default


def set_active_handle(ctx, handle: str) -> str:
    runtime = ctx.setdefault('layout_runtime', {}) if isinstance(ctx, dict) else {}
    runtime['active_handle'] = str(handle or '')
    set_meta(ctx, '|LAYOUT', 'active_handle', runtime['active_handle'])
    return runtime['active_handle']


__all__ = [
    'meta_prefix',
    'state_get',
    'state_set',
    'state_delete',
    'as_dict',
    'get_value',
    'set_value',
    'get_meta',
    'set_meta',
    'set_title',
    'set_prompt',
    'set_view_material',
    'refresh_instance_material',
    'get_active_handle',
    'set_active_handle',
]
