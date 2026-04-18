from __future__ import annotations

from typing import Any

from system.lib.q.roles import normalize_role_name



def attrs_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], dict):
        return dict(value[1])
    return {}


def bool_attr(attrs: dict[str, Any] | None, key: str, default: bool = False) -> bool:
    raw = str((attrs or {}).get(key) or '').strip().lower()
    if raw in {'1', 'true', 'yes', 'on'}:
        return True
    if raw in {'0', 'false', 'no', 'off'}:
        return False
    return bool(default)


def int_attr(attrs: dict[str, Any] | None, key: str, default: int = 1, minimum: int = 1) -> int:
    try:
        return max(int(minimum), int((attrs or {}).get(key, default) or default))
    except Exception:
        return max(int(minimum), int(default))


def flow_attr(tag: str, attrs: dict[str, Any] | None) -> str:
    flow = str((attrs or {}).get('flow') or '').strip().lower()
    if flow in {'top', 'middle', 'bottom'}:
        return flow
    return 'top' if str(tag or '').strip().lower() == 'q' else 'bottom'


def input_attr(attrs: dict[str, Any] | None) -> str:
    return str((attrs or {}).get('input') or '').strip()


def role_attr(attrs: dict[str, Any] | None) -> str:
    return normalize_role_name((attrs or {}).get('role'))


def target_attr(attrs: dict[str, Any] | None, binding_handle: str = '') -> str:
    raw = str((attrs or {}).get('target') or '').strip()
    if raw == '|':
        return str(binding_handle or '').strip()
    return raw


def profile_attr(attrs: dict[str, Any] | None) -> str:
    raw_profile = str((attrs or {}).get('profile') or '').strip()
    return raw_profile or 'default'


def qtarget_attr(attrs: dict[str, Any] | None) -> str:
    return str((attrs or {}).get('qtarget') or '').strip()


def layout_title_from_tree(tree: dict[str, Any] | None, fallback: str = '') -> str:
    if not isinstance(tree, dict):
        return str(fallback or '')
    node = tree.get('tree') if isinstance(tree.get('tree'), dict) else tree
    attrs = dict(node.get('attrs') or {}) if isinstance(node, dict) else {}
    title = str(attrs.get('title') or '').strip()
    return title or str(fallback or '')


def config_for_spec(binding_handle: str, route_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    tag = str(spec.get('tag') or '').strip().lower()
    attrs = attrs_dict(spec.get('attrs') or {})
    target = target_attr(attrs, binding_handle)
    input_target = input_attr(attrs)
    config: dict[str, Any] = {
        'bound_module_name': tag,
        'layout_name': str(route_name or '').strip(),
        'instance_suffix': f"{tag}{int(spec.get('ordinal') or 1)}",
    }
    if target:
        config['target'] = target
    if input_target:
        config['input'] = input_target
    qtarget = qtarget_attr(attrs)
    if qtarget:
        config['qtarget'] = qtarget

    if tag == 'monitor':
        source = target or binding_handle
        config['target'] = f"{source}:buffer"
    elif tag == 'q':
        config['profile'] = profile_attr(attrs)
        module_id = str(attrs.get('id') or '').strip()
        if module_id:
            config['module_id'] = module_id
            config['runtime_root'] = f"{binding_handle}:{module_id}"
        else:
            config['runtime_root'] = binding_handle
        role_name = role_attr(attrs)
        if role_name:
            config['role'] = role_name
    elif tag == 'qmon':
        source = target
        if not source:
            raise ValueError('layout module <qmon> requires target')
        config['source_handle'] = source
    return config


__all__ = [
    'attrs_dict',
    'bool_attr',
    'int_attr',
    'flow_attr',
    'input_attr',
    'role_attr',
    'target_attr',
    'profile_attr',
    'qtarget_attr',
    'layout_title_from_tree',
    'config_for_spec',
]
