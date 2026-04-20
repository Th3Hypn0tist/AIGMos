from __future__ import annotations

import json
import re
from typing import Any, Callable

from system.extensions import (
    assert_extension_symbol_read_allowed,
    assert_extension_symbol_write_allowed,
)
from system.state.api import delete_value, list_symbols as _list_symbols, read_value, write_value

ALL_ROOTS = {"$", "#", "&", "%", "!", "@", "|"}
STATE_ROOTS = {"$", "#", "&"}
RUNTIME_ROOTS = ALL_ROOTS - STATE_ROOTS
VALUE_KEY = "__value__"

_SEGMENT_RE = r"[A-Za-z0-9._]+"
_SYMBOL_BODY_RE = rf"[\$#&%!@|]{_SEGMENT_RE}(?::{_SEGMENT_RE})*"
_SYMBOL_RE = re.compile(rf"({_SYMBOL_BODY_RE})")
_BRACKET_SYMBOL_RE = re.compile(rf"\[({_SYMBOL_BODY_RE})\]")


class SymbolError(ValueError):
    pass


def _ensure_symbol_read_allowed(state, symbol: str) -> None:
    try:
        assert_extension_symbol_read_allowed(state, symbol)
    except Exception as exc:
        raise SymbolError(str(exc)) from exc


def _ensure_symbol_write_allowed(state, symbol: str) -> None:
    try:
        assert_extension_symbol_write_allowed(state, symbol)
    except Exception as exc:
        raise SymbolError(str(exc)) from exc


def symbol_root(symbol: str) -> str:
    raw = str(symbol or "").strip()
    if not raw:
        raise SymbolError("symbol cannot be empty")
    root = raw[0]
    if root not in ALL_ROOTS:
        raise SymbolError(f"invalid symbol root: {raw}")
    return root


def validate_symbol(
    symbol: str,
    *,
    allow_bare_root: bool = False,
    allowed: str | set[str] | tuple[str, ...] | list[str] | None = None,
    role: str = "symbol",
) -> str:
    raw = str(symbol or "").strip()
    if not raw:
        raise SymbolError(f"{role} cannot be empty")

    root = symbol_root(raw)
    if allowed is not None and root not in set(allowed):
        raise SymbolError(f"{role} must start with one of: {''.join(sorted(set(allowed)))}")

    body = raw[1:]
    if not body:
        if allow_bare_root:
            return root
        raise SymbolError(f"{role} cannot be bare root: {raw}")

    if raw.endswith(":") or "::" in raw:
        raise SymbolError(f"invalid {role}: {raw}")

    parts = body.split(":")
    if not all(re.fullmatch(_SEGMENT_RE, part or "") for part in parts):
        raise SymbolError(f"invalid {role}: {raw}")

    return root


def is_symbol_ref(symbol: str) -> bool:
    try:
        validate_symbol(symbol, allow_bare_root=False)
        return True
    except Exception:
        return False


def state_side_only(symbol: str, verb: str) -> None:
    if symbol_root(symbol) not in STATE_ROOTS:
        raise SymbolError(f"{verb} requires state-side symbol")


def list_symbols(state) -> list[str]:
    return _list_symbols(state)


def _has_exact_symbol(state, symbol: str) -> bool:
    target = str(symbol or "").strip()
    return target in set(list_symbols(state))


def _child_symbols(state, symbol: str) -> list[str]:
    prefix = str(symbol or "").strip() + ":"
    return sorted(item for item in list_symbols(state) if item.startswith(prefix))


def read_symbol_value(state, symbol: str, default: Any = None) -> Any:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_read_allowed(state, symbol)
    return read_value(state, symbol, default)


def write_symbol_value(state, symbol: str, value: Any, *, writer: str, op: str = "set") -> dict[str, Any]:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_write_allowed(state, symbol)
    return write_value(state, symbol, value, writer=writer, op=op)


def _normalize_branch_value(node: Any) -> Any:
    if isinstance(node, dict):
        child_keys = [key for key in node.keys() if key != VALUE_KEY]
        if child_keys and all(str(key).isdigit() for key in child_keys):
            ordered = sorted((int(str(key)), node[key]) for key in child_keys)
            if ordered and ordered[0][0] == 0 and ordered[-1][0] == len(ordered) - 1:
                values = [_normalize_branch_value(value) for _, value in ordered]
                if VALUE_KEY in node:
                    merged = {VALUE_KEY: node[VALUE_KEY]}
                    for idx, value in enumerate(values):
                        merged[str(idx)] = value
                    return merged
                return values
        return {str(key): _normalize_branch_value(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_normalize_branch_value(item) for item in node]
    return node


def _set_nested(tree: dict[str, Any], parts: list[str], value: Any) -> None:
    cur = tree
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    leaf = parts[-1]
    existing = cur.get(leaf)
    if isinstance(existing, dict) and isinstance(value, dict):
        merged = dict(existing)
        merged.update(value)
        cur[leaf] = merged
    else:
        cur[leaf] = value


def collect_branch_tree(state, symbol: str) -> Any:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_read_allowed(state, symbol)
    descendants = _child_symbols(state, symbol)
    if not descendants:
        return None

    base = str(symbol or "").strip()
    tree: dict[str, Any] = {}
    for child in descendants:
        rel = child[len(base) + 1 :]
        if not rel:
            continue
        value = read_value(state, child, None)
        parts = [part for part in rel.split(":") if part]
        if not parts:
            continue
        _set_nested(tree, parts, value)
    return _normalize_branch_value(tree)


def _merge_exact_and_branch(exact: Any, branch: Any) -> Any:
    if branch is None:
        return exact
    if exact is None:
        return branch
    if isinstance(branch, dict):
        merged = {VALUE_KEY: exact}
        merged.update(branch)
        return merged
    if isinstance(branch, list):
        merged = {VALUE_KEY: exact}
        for idx, item in enumerate(branch):
            merged[str(idx)] = item
        return merged
    return {VALUE_KEY: exact, "value": branch}


def resolve_raw_exact(state, symbol: str) -> Any:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_read_allowed(state, symbol)
    exact_exists = _has_exact_symbol(state, symbol)
    exact = read_value(state, symbol, None) if exact_exists else None
    branch = collect_branch_tree(state, symbol)
    if exact_exists:
        return _merge_exact_and_branch(exact, branch)
    return branch


def stringify_resolved(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def resolve_exact(state, symbol: str) -> str:
    value = resolve_raw_exact(state, symbol)
    if value is None:
        raise SymbolError(f"symbol not found: {symbol}")
    return stringify_resolved(value)


def symbol_exists_or_has_children(state, symbol: str) -> bool:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_read_allowed(state, symbol)
    return _has_exact_symbol(state, symbol) or bool(_child_symbols(state, symbol))


def try_parse_structured_json(value: Any) -> Any:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text[0] not in "[{" or text[-1] not in "]}":
        return None
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def dump_value(value: Any) -> str:
    return stringify_resolved(value)


def _is_structured_value(value: Any) -> bool:
    return isinstance(value, (dict, list))


def _freeze_value(frozen: dict[str, str], counter: list[int], value: Any) -> str:
    idx = int(counter[0])
    counter[0] = idx + 1
    token = f"\\x00AIGMOS_FROZEN_{idx}\\x00"
    frozen[token] = stringify_resolved(value)
    return token


def _restore_frozen(text: str, frozen: dict[str, str]) -> str:
    current = str(text or "")
    for token, value in frozen.items():
        current = current.replace(token, value)
    return current


def _protect_bracket_tokens(text: str, bracket_pattern: re.Pattern[str]) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        idx = len(protected)
        token = f"\\x00AIGMOS_BRACKET_{idx}\\x00"
        protected[token] = str(match.group(0) or "")
        return token

    return bracket_pattern.sub(_replace, str(text or "")), protected


def _restore_bracket_tokens(text: str, protected: dict[str, str]) -> str:
    current = str(text or "")
    for token, value in protected.items():
        current = current.replace(token, value)
    return current


def _resolve_token_value(resolve_token: Callable[[str], Any], token: str) -> tuple[bool, Any]:
    result = resolve_token(token)
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
        return bool(result[0]), result[1]
    return (result is not None), result


def expand_text_with_token_resolver(
    text: str,
    *,
    plain_pattern: re.Pattern[str],
    bracket_pattern: re.Pattern[str],
    resolve_token: Callable[[str], Any],
    strict: bool = True,
    max_bracket_passes: int = 16,
) -> str:
    current = str(text or "")
    frozen: dict[str, str] = {}
    counter = [0]

    protected_text, protected = _protect_bracket_tokens(current, bracket_pattern)

    def _replace_plain(match: re.Match[str]) -> str:
        token = str(match.group(1) or "")
        found, value = _resolve_token_value(resolve_token, token)
        if not found:
            if strict:
                raise SymbolError(f"symbol not found: {token}")
            return token
        if _is_structured_value(value):
            return _freeze_value(frozen, counter, value)
        return stringify_resolved(value)

    current = plain_pattern.sub(_replace_plain, protected_text)
    current = _restore_bracket_tokens(current, protected)

    passes = max(0, int(max_bracket_passes or 0))
    for _ in range(passes):
        changed = False

        def _replace_bracket(match: re.Match[str]) -> str:
            nonlocal changed
            token = str(match.group(1) or "")
            found, value = _resolve_token_value(resolve_token, token)
            if not found:
                if strict:
                    raise SymbolError(f"symbol not found: {token}")
                return str(match.group(0) or "")
            changed = True
            if _is_structured_value(value):
                return _freeze_value(frozen, counter, value)
            return stringify_resolved(value)

        updated = bracket_pattern.sub(_replace_bracket, current)
        current = updated
        if not changed:
            break

    return _restore_frozen(current, frozen)


def expand_text_recursive_with_token_resolver(
    text: str,
    *,
    plain_pattern: re.Pattern[str],
    bracket_pattern: re.Pattern[str],
    resolve_token: Callable[[str], Any],
    strict: bool = True,
    max_passes: int = 16,
) -> str:
    current = str(text or "")
    frozen: dict[str, str] = {}
    counter = [0]
    passes = max(1, int(max_passes or 1))

    for _ in range(passes):
        protected_text, protected = _protect_bracket_tokens(current, bracket_pattern)
        changed = False

        def _replace_plain(match: re.Match[str]) -> str:
            nonlocal changed
            token = str(match.group(1) or "")
            found, value = _resolve_token_value(resolve_token, token)
            if not found:
                if strict:
                    raise SymbolError(f"symbol not found: {token}")
                return token
            replacement = _freeze_value(frozen, counter, value) if _is_structured_value(value) else stringify_resolved(value)
            if replacement != token:
                changed = True
            return replacement

        updated = plain_pattern.sub(_replace_plain, protected_text)
        updated = _restore_bracket_tokens(updated, protected)

        def _replace_bracket(match: re.Match[str]) -> str:
            nonlocal changed
            token = str(match.group(1) or "")
            found, value = _resolve_token_value(resolve_token, token)
            if not found:
                if strict:
                    raise SymbolError(f"symbol not found: {token}")
                return str(match.group(0) or "")
            replacement = _freeze_value(frozen, counter, value) if _is_structured_value(value) else stringify_resolved(value)
            changed = True
            return replacement

        updated = bracket_pattern.sub(_replace_bracket, updated)
        current = updated
        if not changed:
            break

    return _restore_frozen(current, frozen)


def expand_symbols_in_text(state, text: str, *, max_passes: int = 16, strict: bool = True) -> str:
    return expand_text_with_token_resolver(
        text,
        plain_pattern=_SYMBOL_RE,
        bracket_pattern=_BRACKET_SYMBOL_RE,
        resolve_token=lambda token: resolve_raw_exact(state, token),
        strict=strict,
        max_bracket_passes=max_passes,
    )


def expand_symbols_recursive_in_text(state, text: str, *, max_passes: int = 16, strict: bool = True) -> str:
    return expand_text_recursive_with_token_resolver(
        text,
        plain_pattern=_SYMBOL_RE,
        bracket_pattern=_BRACKET_SYMBOL_RE,
        resolve_token=lambda token: resolve_raw_exact(state, token),
        strict=strict,
        max_passes=max_passes,
    )


def clear_symbol_tree(state, symbol: str, *, writer: str, op: str = "clear_symbol_tree") -> None:
    validate_symbol(symbol, allow_bare_root=False)
    _ensure_symbol_write_allowed(state, symbol)
    targets = [item for item in list_symbols(state) if item == symbol or item.startswith(symbol + ":")]
    for item in sorted(targets, key=len, reverse=True):
        out = delete_value(state, item, writer=writer, op=op)
        if out.get("error"):
            raise SymbolError(str(out["error"]))


__all__ = [
    "ALL_ROOTS",
    "STATE_ROOTS",
    "RUNTIME_ROOTS",
    "VALUE_KEY",
    "SymbolError",
    "symbol_root",
    "validate_symbol",
    "is_symbol_ref",
    "state_side_only",
    "list_symbols",
    "read_symbol_value",
    "write_symbol_value",
    "collect_branch_tree",
    "resolve_raw_exact",
    "resolve_exact",
    "symbol_exists_or_has_children",
    "stringify_resolved",
    "try_parse_structured_json",
    "dump_value",
    "expand_text_with_token_resolver",
    "expand_text_recursive_with_token_resolver",
    "expand_symbols_in_text",
    "expand_symbols_recursive_in_text",
    "clear_symbol_tree",
]
