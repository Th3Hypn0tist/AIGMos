from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from system.cs.lib.ops import get_subtree, state_side_only
from system.cs.state_ops import get_optional
from system.cs.symbol_rules import require_symbol
from system.extensions import (
    active_command_is_extension,
    assert_extension_symbol_read_allowed,
    extension_write_path_allowed,
)

_VALUE_KEY = "__value__"
_SYMBOL_ROOTS = "$#&%@!|"


def is_symbol(token: str) -> bool:
    return isinstance(token, str) and bool(token) and token[0] in _SYMBOL_ROOTS


def resolve_dest_path(parser, token: str) -> Path:
    raw = token

    if is_symbol(token):
        try:
            assert_extension_symbol_read_allowed(parser.state, token)
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        value = get_optional(parser.state, token)
        if value in (None, ""):
            raise ValueError(f"destination symbol not found: {token}")
        raw = str(value)

    path = Path(str(raw)).expanduser()
    if active_command_is_extension(parser.state) and not extension_write_path_allowed(str(path)):
        raise ValueError(f"forbidden extension destination path: {path}")
    return path


def export_text(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.file")
    require_symbol(src)

    items = get_subtree(parser.state, src)
    if len(items) != 1:
        raise ValueError("export.file source must resolve to one string")

    symbol, value = items[0]
    if symbol != src or not isinstance(value, str):
        raise ValueError("export.file source must resolve to one string")

    dst = resolve_dest_path(parser, dst_token)
    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(value, encoding="utf-8")


def export_json(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.json")
    require_symbol(src)

    value = _resolve_json_value(parser, src)
    dst = resolve_dest_path(parser, dst_token)

    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def export_code(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.code")
    require_symbol(src)

    items = get_subtree(parser.state, src)
    if not items:
        raise ValueError("source not found")

    dst = resolve_dest_path(parser, dst_token)

    exact_found = False
    exact_value = None
    child_items = []

    for symbol, value in items:
        if symbol == src:
            exact_found = True
            exact_value = value
        else:
            child_items.append((symbol, value))

    if exact_found and child_items:
        raise ValueError("export.code source cannot have both value and children")

    if child_items:
        require_symbol(src, allowed="#", role="export.code subtree source")
        files = _collect_tree_files(src, child_items)
        _write_code_tree(dst, files)
        return

    if not exact_found:
        raise ValueError("source not found")

    if isinstance(exact_value, dict):
        files = _collect_manifest_files(exact_value)
        _write_code_tree(dst, files)
        return

    if isinstance(exact_value, str):
        manifest = _try_parse_manifest_root(exact_value)
        if manifest is not None:
            files = _collect_manifest_files(manifest)
            _write_code_tree(dst, files)
            return

        _write_single_file(dst, exact_value)
        return

    raise ValueError("export.code leaf source must be string or object")


def _resolve_json_value(parser, src: str):
    items = get_subtree(parser.state, src)
    if not items:
        raise ValueError("source not found")

    if len(items) == 1 and items[0][0] == src:
        return items[0][1]

    sep = ":" if src.startswith("#") else "."
    tree = {}

    for symbol, value in items:
        if symbol == src:
            tree[_VALUE_KEY] = value
            continue

        rel = symbol[len(src + sep):]
        parts = rel.split(sep) if rel else []

        cur = tree
        for part in parts[:-1]:
            nxt = cur.get(part)
            if nxt is None:
                nxt = {}
                cur[part] = nxt
            elif not isinstance(nxt, dict):
                nxt = {_VALUE_KEY: nxt}
                cur[part] = nxt
            cur = nxt

        if not parts:
            tree[_VALUE_KEY] = value
            continue

        leaf = parts[-1]
        existing = cur.get(leaf)

        if isinstance(existing, dict):
            existing[_VALUE_KEY] = value
        elif existing is not None:
            cur[leaf] = {_VALUE_KEY: existing}
            cur[leaf][_VALUE_KEY] = value
        else:
            cur[leaf] = value

    return _normalize_numeric_nodes(tree)


def _normalize_numeric_nodes(value):
    if isinstance(value, list):
        return [_normalize_numeric_nodes(item) for item in value]

    if not isinstance(value, dict):
        return value

    normalized = {key: _normalize_numeric_nodes(val) for key, val in value.items()}

    keys = [key for key in normalized.keys() if key != _VALUE_KEY]
    if _VALUE_KEY in normalized:
        return normalized

    if not keys:
        return normalized

    if not all(key.isdigit() for key in keys):
        return normalized

    ordered = sorted(int(key) for key in keys)
    if ordered != list(range(len(ordered))):
        return normalized

    return [normalized[str(idx)] for idx in ordered]


def _try_parse_manifest_root(raw: str):
    try:
        value = json.loads(raw)
    except Exception:
        return None

    if not isinstance(value, dict):
        return None

    return value


def _collect_manifest_files(root: dict) -> dict[tuple[str, ...], str]:
    files: dict[tuple[str, ...], str] = {}
    dirs: set[tuple[str, ...]] = set()
    _walk_manifest_node(root, (), files, dirs)
    if not files:
        raise ValueError("export.code manifest is empty")
    return files


def _walk_manifest_node(node: Any, path: tuple[str, ...], files: dict[tuple[str, ...], str], dirs: set[tuple[str, ...]]) -> None:
    if isinstance(node, str):
        if not path:
            raise ValueError("export.code manifest root cannot be a string")
        files[path] = node
        return

    if not isinstance(node, dict):
        raise ValueError("export.code manifest supports only objects and string leaves")

    for key, value in node.items():
        name = str(key).strip()
        if not name:
            raise ValueError("export.code manifest contains empty path segment")
        next_path = path + (name,)
        if isinstance(value, dict):
            dirs.add(next_path)
        _walk_manifest_node(value, next_path, files, dirs)


def _collect_tree_files(src: str, items: list[tuple[str, Any]]) -> dict[tuple[str, ...], str]:
    files: dict[tuple[str, ...], str] = {}
    prefix = src + ":"

    for symbol, value in items:
        rel = symbol[len(prefix):] if symbol.startswith(prefix) else ""
        parts = tuple(part for part in rel.split(":") if part)
        if not parts:
            continue
        if not isinstance(value, str):
            raise ValueError(f"export.code subtree leaf must be string: {symbol}")
        files[parts] = value

    if not files:
        raise ValueError("export.code subtree is empty")
    return files


def _write_single_file(dst: Path, value: str) -> None:
    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(value, encoding="utf-8")


def _write_code_tree(dst: Path, files: dict[tuple[str, ...], str]) -> None:
    if dst.exists() and dst.is_file():
        raise ValueError(f"destination is a file: {dst}")

    dst.mkdir(parents=True, exist_ok=True)

    for parts, value in files.items():
        path = dst.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
