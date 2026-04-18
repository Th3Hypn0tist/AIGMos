from __future__ import annotations

import os
from fnmatch import fnmatch
from pathlib import Path

from system.cs.lib.ops import list_symbols, remove_subtree
from system.cs.state_ops import get_optional, set_result
from system.cs.symbol_rules import require_symbol
from system.extensions import (
    active_command_is_extension,
    assert_extension_symbol_read_allowed,
    extension_read_path_allowed,
)

_SYMBOL_ROOTS = "$#&%@!|"

_DEFAULT_IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.sqlite",
    "*.db",
    ".DS_Store",
    "Thumbs.db",
    ".git",
    ".venv",
    "node_modules",
]


def is_symbol(token: str) -> bool:
    return isinstance(token, str) and bool(token) and token[0] in _SYMBOL_ROOTS


def resolve_source_path(parser, token: str) -> Path:
    raw = token

    if is_symbol(token):
        try:
            assert_extension_symbol_read_allowed(parser.state, token)
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        value = get_optional(parser.state, token)
        if value in (None, ""):
            raise ValueError(f"source symbol not found: {token}")
        raw = str(value)

    path = Path(str(raw)).expanduser()
    if active_command_is_extension(parser.state) and not extension_read_path_allowed(str(path)):
        raise ValueError(f"forbidden extension source path: {path}")
    if not path.exists():
        raise ValueError(f"source path not found: {path}")
    return path


def read_text_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"source is not a file: {path}")

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"file is not valid utf-8 text: {path}") from None


def validate_data_symbol(symbol: str) -> None:
    require_symbol(symbol, allowed="$#&")


def validate_code_root(symbol: str) -> None:
    require_symbol(symbol, allowed="#", role="import.code target")


def import_code_tree(parser, src_path: Path, dst_root: str, *, writer: str = "parser:import.code") -> None:
    validate_code_root(dst_root)

    items = _collect_code_items(parser, src_path)
    _clear_prefix_if_exists(parser.state, dst_root, writer=writer)

    set_result(parser.state, dst_root, "{}", writer=writer, op="import_code_root_set")

    for rel_key, text in items:
        target = f"{dst_root}:{rel_key}" if rel_key else dst_root
        set_result(parser.state, target, text, writer=writer, op="import_code_item_set")


def _collect_code_items(parser, src_path: Path) -> list[tuple[str, str]]:
    if src_path.is_file():
        if _is_ignored(parser, src_path.name):
            return []

        _validate_segments([src_path.name])
        return [(src_path.name, read_text_file(src_path))]

    if not src_path.is_dir():
        raise ValueError(f"source is neither file nor directory: {src_path}")

    items: list[tuple[str, str]] = []

    for root, dirs, files in os.walk(src_path, topdown=True):
        root_path = Path(root)
        rel_root = root_path.relative_to(src_path)

        keep_dirs = []
        for dirname in dirs:
            rel_parts = list(rel_root.parts) + [dirname]
            if not _path_is_ignored(parser, rel_parts):
                keep_dirs.append(dirname)
        dirs[:] = sorted(keep_dirs)

        for filename in sorted(files):
            rel_parts = list(rel_root.parts) + [filename]

            if _path_is_ignored(parser, rel_parts):
                continue

            _validate_segments(rel_parts)

            path = root_path / filename
            rel_key = ":".join(rel_parts)
            items.append((rel_key, read_text_file(path)))

    return items


def _validate_segments(parts: list[str]) -> None:
    for segment in parts:
        if not segment:
            raise ValueError("invalid empty path segment")
        if segment.startswith("."):
            raise ValueError(f"invalid path segment: {segment}")
        if segment.endswith("."):
            raise ValueError(f"invalid path segment: {segment}")

        for ch in segment:
            if not (ch.isalnum() or ch in "._"):
                raise ValueError(f"invalid path segment: {segment}")


def _clear_prefix_if_exists(state, prefix: str, *, writer: str) -> None:
    for symbol in list_symbols(state):
        if symbol == prefix or symbol.startswith(prefix + ":"):
            remove_subtree(state, prefix, writer=writer, op="import_code_clear_prefix")
            return


def _get_ignore_patterns(parser) -> list[str]:
    prefix = "#SYSTEM:config:import:code:ignore:"
    symbols = [s for s in list_symbols(parser.state) if s.startswith(prefix)]

    def sort_key(symbol: str):
        tail = symbol[len(prefix):]
        return (0, int(tail)) if tail.isdigit() else (1, tail)

    patterns = list(_DEFAULT_IGNORE_PATTERNS)

    for symbol in sorted(symbols, key=sort_key):
        value = get_optional(parser.state, symbol)
        if value is None:
            continue

        pattern = str(value).strip()
        if pattern:
            patterns.append(pattern)

    return patterns


def _path_is_ignored(parser, rel_parts: list[str]) -> bool:
    patterns = _get_ignore_patterns(parser)
    joined = "/".join(rel_parts)

    for segment in rel_parts:
        if _matches_any(patterns, segment):
            return True

    return _matches_any(patterns, joined)


def _is_ignored(parser, name: str) -> bool:
    patterns = _get_ignore_patterns(parser)
    return _matches_any(patterns, name)


def _matches_any(patterns: list[str], value: str) -> bool:
    for pattern in patterns:
        if fnmatch(value, pattern):
            return True
    return False
