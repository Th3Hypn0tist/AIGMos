from __future__ import annotations


def normalize_handle(raw: str) -> str:
    text = str(raw or '').strip()
    if not text:
        raise ValueError('layout handle cannot be empty')
    if not text.startswith('|'):
        raise ValueError('layout handle must start with |')
    body = text[1:].strip()
    if not body:
        raise ValueError('layout handle cannot be empty')

    owner, sep, module_id = body.partition(':')
    if ':' in module_id:
        raise ValueError('layout handle can contain at most one :')

    parts = [part for part in owner.split('.') if part != '']
    if not parts:
        raise ValueError('layout handle cannot be empty')
    head = parts[0].upper()
    tail = parts[1:]
    normalized_owner = '.'.join([head, *tail])
    if sep:
        module_clean = str(module_id or '').strip()
        if not module_clean:
            raise ValueError('layout module id cannot be empty')
        return f'|{normalized_owner}:{module_clean}'
    return f'|{normalized_owner}'


def route_name(route: str) -> str:
    token = str(route or '').strip()
    if token.startswith('/'):
        token = token[1:]
    return token.strip()


def layout_handle_from_route(route: str) -> str:
    token = route_name(route)
    if not token:
        raise ValueError('layout route cannot be empty')
    base, dot, suffix = token.partition('.')
    head = base.upper()
    return f'|{head}.{suffix}' if suffix else f'|{head}'


def display_name(handle: str) -> str:
    return str(handle or '').strip().lstrip('|')


def binding_name(binding_handle: str) -> str:
    return display_name(binding_handle).split('.', 1)[0]


def instance_suffix(binding_handle: str, tag: str, ordinal: int) -> str:
    return f'{tag}{int(ordinal)}'


def instance_handle(binding_handle: str, module_ref: str) -> str:
    base = normalize_handle(binding_handle)
    ref = str(module_ref or '').strip()
    if not ref:
        raise ValueError('layout module ref cannot be empty')
    if ':' in ref:
        raise ValueError('layout module ref cannot contain :')
    return f'{base}:{ref}'


def state_root_for_handle(raw_handle: str) -> str:
    clean = str(raw_handle or '').strip()
    if not clean:
        raise ValueError('q runtime root is required')
    if clean.startswith('|'):
        if ':' in clean:
            return clean
        return normalize_handle(clean)
    raise ValueError('q runtime root must be in | namespace')


def state_root_for_target(raw_target: str) -> str:
    clean = str(raw_target or '').strip()
    if not clean:
        return ''
    if clean.startswith('|'):
        if ':' in clean:
            return clean
        return normalize_handle(clean)
    return ''
