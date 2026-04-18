from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from system.state.api import delete_value, list_symbols, read_value, write_value

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HELP_DIRS = (
    (PROJECT_ROOT / 'system' / 'library' / 'help', '#HELP'),
)
ROLE_DIRS = (
    (PROJECT_ROOT / 'extensions' / 'roles', '#ROLES'),
    (PROJECT_ROOT / 'system' / 'library' / 'roles', '#ROLES:system'),
)
PROMPT_DIRS = (
    (PROJECT_ROOT / 'extensions' / 'prompts', '#P'),
    (PROJECT_ROOT / 'system' / 'library' / 'prompts', '#P:system'),
)
ROUTINE_DIRS = (
    (PROJECT_ROOT / 'extensions' / 'routines', '#R'),
    (PROJECT_ROOT / 'system' / 'library' / 'routines', '#R:system'),
)


def _state_set(state, symbol: str, value: Any, *, writer: str = 'reload', op: str = 'reload_set') -> None:
    out = write_value(state, symbol, value, writer=writer, op=op)
    if out.get('error'):
        raise RuntimeError(str(out['error']))


def _state_get(state, symbol: str, default: Any = None) -> Any:
    out = read_value(state, symbol, default)
    if isinstance(out, dict) and 'result' in out and 'error' in out:
        if out.get('error'):
            return default
        result = out.get('result', default)
        return default if result is None else result
    return default if out is None else out


def _state_delete(state, symbol: str, *, writer: str = 'reload', op: str = 'reload_delete') -> None:
    out = delete_value(state, symbol, writer=writer, op=op)
    if out.get('error'):
        raise RuntimeError(str(out['error']))


def _clear_prefix(state, prefix: str) -> None:
    doomed = [symbol for symbol in list_symbols(state) if symbol == prefix or symbol.startswith(prefix + ':')]
    for symbol in sorted(doomed, reverse=True):
        _state_delete(state, symbol)


def _symbol_from_relative(base_symbol: str, rel: Path) -> str:
    parts = list(rel.parts)
    if not parts:
        return base_symbol
    leaf = parts[-1]
    head = parts[:-1]
    return ':'.join([base_symbol, *head, leaf])


def _import_text_tree(state, root: Path, base_symbol: str, *, exts: set[str] | None = None) -> list[str]:
    written: list[str] = []
    if not root.is_dir():
        return written
    allowed = {item.lower() for item in (exts or set())}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        if allowed and path.suffix.lower() not in allowed:
            continue
        rel = path.relative_to(root)
        symbol = _symbol_from_relative(base_symbol, rel)
        _state_set(state, symbol, path.read_text(encoding='utf-8'))
        written.append(symbol)
    return written


def _import_roles_from_root(state, root: Path, base_symbol: str, *, role_filter: str = '', strip_leading_system: bool = False) -> list[str]:
    written: list[str] = []
    if not root.is_dir():
        return written
    wanted = str(role_filter or '').strip().replace('\\', '/').strip('/')
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in {'.role', '.system'}:
            continue
        rel = path.relative_to(root)
        rel_parts = list(rel.parts)
        if strip_leading_system and rel_parts[:1] == ['system']:
            rel_parts = rel_parts[1:]
            rel = Path(*rel_parts) if rel_parts else Path(path.name)
        norm_rel = '/'.join(rel.parts)
        if wanted:
            if norm_rel not in {wanted + '.role', wanted + '.system'}:
                continue
        symbol = _symbol_from_relative(base_symbol, rel)
        if path.suffix.lower() == '.role':
            payload = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(payload, dict):
                raise ValueError(f'role file must contain JSON object: {path}')
            _state_set(state, symbol, payload)
        else:
            _state_set(state, symbol, path.read_text(encoding='utf-8'))
        written.append(symbol)
    return written


def reload_help(state) -> list[str]:
    _clear_prefix(state, '#HELP')
    written: list[str] = []
    for root, base_symbol in HELP_DIRS:
        written.extend(_import_text_tree(state, root, base_symbol, exts={'.md', '.txt'}))
    return written


def reload_prompts(state) -> list[str]:
    _clear_prefix(state, '#P')
    written: list[str] = []
    for root, base_symbol in PROMPT_DIRS:
        written.extend(_import_text_tree(state, root, base_symbol))
    return written


def reload_routines(state) -> list[str]:
    _clear_prefix(state, '#R')
    written: list[str] = []
    for root, base_symbol in ROUTINE_DIRS:
        written.extend(_import_text_tree(state, root, base_symbol))
    return written


def reload_roles(state) -> list[str]:
    _clear_prefix(state, '#ROLES')
    written: list[str] = []
    for root, base_symbol in ROLE_DIRS:
        strip_leading_system = str(base_symbol).startswith('#ROLES:system')
        written.extend(_import_roles_from_root(state, root, base_symbol, strip_leading_system=strip_leading_system))
    return written


def reload_role(state, role_name: str) -> list[str]:
    wanted = str(role_name or '').strip().replace('\\', '/').strip('/')
    if not wanted:
        raise ValueError('role name required')
    strip_leading_system = False
    if wanted.startswith('system/'):
        root = PROJECT_ROOT / 'system' / 'library' / 'roles'
        base_symbol = '#ROLES:system'
        rel = wanted[len('system/'):].strip('/')
        strip_leading_system = True
        role_symbol = '#ROLES:system:' + rel.replace('/', ':') + '.role'
        system_symbol = '#ROLES:system:' + rel.replace('/', ':') + '.system'
    else:
        root = PROJECT_ROOT / 'extensions' / 'roles'
        base_symbol = '#ROLES'
        rel = wanted
        role_symbol = '#ROLES:' + wanted.replace('/', ':') + '.role'
        system_symbol = '#ROLES:' + wanted.replace('/', ':') + '.system'
    for prefix in (role_symbol, system_symbol):
        doomed = [symbol for symbol in list_symbols(state) if symbol == prefix]
        for symbol in doomed:
            _state_delete(state, symbol)
    written = _import_roles_from_root(state, root, base_symbol, role_filter=rel, strip_leading_system=strip_leading_system)
    if not written:
        raise ValueError(f'role not found: {wanted}')
    return written


def run_init_cs(parser, path: Path | None = None) -> list[str]:
    init_path = path or (PROJECT_ROOT / 'system' / 'init.cs')
    if not init_path.is_file():
        return []
    executed: list[str] = []
    for raw in init_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        err = parser.parse(line)
        if err:
            raise RuntimeError(str(err))
        executed.append(line)
    return executed
