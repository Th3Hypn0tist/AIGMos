# system/cs/lib/file_export.py

from __future__ import annotations

import json
from pathlib import Path

from system.cs.lib.ops import get_subtree, state_side_only, validate_symbol


_SYMBOL_ROOTS = "$#&%@!"
_VALUE_KEY = "__value__"


def is_symbol(token: str) -> bool:
    return isinstance(token, str) and bool(token) and token[0] in _SYMBOL_ROOTS


def resolve_dest_path(parser, token: str) -> Path:
    raw = token

    if is_symbol(token):
        out = parser.state.get(token)
        if out["error"]:
            raise ValueError(out["error"])
        if out["result"] in (None, ""):
            raise ValueError(f"destination symbol not found: {token}")

        value = out["result"]
        if isinstance(value, (dict, list)):
            raise ValueError(f"destination symbol is not scalar: {token}")

        raw = str(value)

    return Path(str(raw)).expanduser()


def export_text(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.file")
    validate_symbol(src)

    out = parser.state.get(src)
    if out["error"]:
        raise ValueError(out["error"])

    value = out["result"]
    if not isinstance(value, str):
        raise ValueError("export.file source must resolve to one string")

    items = get_subtree(parser.state, src)
    if len(items) != 1 or items[0][0] != src:
        raise ValueError("export.file source must resolve to one string")

    dst = resolve_dest_path(parser, dst_token)
    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(value, encoding="utf-8")


def export_json(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.json")
    validate_symbol(src)

    value = _resolve_json_value(parser, src)
    dst = resolve_dest_path(parser, dst_token)

    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def export_code(parser, src: str, dst_token: str) -> None:
    state_side_only(src, "export.code")
    validate_symbol(src)

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
        if not src.startswith("#"):
            raise ValueError("export.code subtree source must start with #")
        files = _collect_tree_files(src, child_items)
        _write_code_tree(dst, files)
        return

    if not exact_found:
        raise ValueError("source not found")

    if not isinstance(exact_value, str):
        raise ValueError("export.code leaf source must be string")

    manifest = _try_parse_manifest_root(exact_value)
    if manifest is not None:
        files = _collect_manifest_files(manifest)
        _write_code_tree(dst, files)
        return

    _write_single_file(dst, exact_value)


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


def _walk_manifest_node(
    node: dict,
    prefix: tuple[str, ...],
    files: dict[tuple[str, ...], str],
    dirs: set[tuple[str, ...]],
) -> None:
    for raw_key, value in node.items():
        if not isinstance(raw_key, str) or not raw_key:
            raise ValueError("export.code manifest keys must be non-empty strings")

        parts = tuple(_split_export_path(raw_key))
        full = prefix + parts

        if isinstance(value, str):
            _add_export_file(files, dirs, full, value)
            continue

        if isinstance(value, dict):
            _add_export_dir(files, dirs, full)
            _walk_manifest_node(value, full, files, dirs)
            continue

        raise ValueError("export.code manifest values must be string or object")


def _collect_tree_files(src: str, child_items: list[tuple[str, object]]) -> dict[tuple[str, ...], str]:
    prefix = src + ":"
    files: dict[tuple[str, ...], str] = {}
    dirs: set[tuple[str, ...]] = set()

    for symbol, value in child_items:
        if not isinstance(value, str):
            raise ValueError(f"export.code value must be string: {symbol}")

        rel = symbol[len(prefix):]
        if not rel:
            raise ValueError(f"invalid code source: {symbol}")

        parts = tuple(rel.split(":"))
        _add_export_file(files, dirs, parts, value)

    if not files:
        raise ValueError("export.code source is empty")

    return files


def _add_export_dir(
    files: dict[tuple[str, ...], str],
    dirs: set[tuple[str, ...]],
    path: tuple[str, ...],
) -> None:
    if not path:
        raise ValueError("invalid export.code directory path")
    if path in files:
        raise ValueError(f"export.code path conflict: {'/'.join(path)}")
    dirs.add(path)


def _add_export_file(
    files: dict[tuple[str, ...], str],
    dirs: set[tuple[str, ...]],
    path: tuple[str, ...],
    value: str,
) -> None:
    if not path:
        raise ValueError("invalid export.code file path")
    if path in dirs:
        raise ValueError(f"export.code path conflict: {'/'.join(path)}")
    if path in files:
        raise ValueError(f"export.code duplicate file path: {'/'.join(path)}")

    for i in range(1, len(path)):
        parent = path[:i]
        if parent in files:
            raise ValueError(f"export.code file/dir conflict: {'/'.join(parent)}")
        dirs.add(parent)

    files[path] = value


def _split_export_path(raw: str) -> list[str]:
    if raw.startswith("/"):
        raise ValueError(f"export.code path must be relative: {raw}")
    if "\\" in raw:
        raise ValueError(f"export.code path must use '/': {raw}")

    parts = raw.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"invalid export.code path: {raw}")

    return parts


def _write_single_file(dst: Path, value: str) -> None:
    if dst.exists() and dst.is_dir():
        raise ValueError(f"destination is a directory: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(value, encoding="utf-8")


def _write_code_tree(dst: Path, files: dict[tuple[str, ...], str]) -> None:
    if dst.exists() and dst.is_file():
        raise ValueError(f"destination is a file: {dst}")

    dst.mkdir(parents=True, exist_ok=True)

    for rel_parts, value in sorted(files.items()):
        file_path = dst.joinpath(*rel_parts)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(value, encoding="utf-8")
