from __future__ import annotations

from typing import Any, Optional

from system.lib.symbols import (
    expand_symbols_in_text,
    resolve_raw_exact,
    validate_symbol,
)


def symbol_has_children(parser, symbol: str) -> bool:
    try:
        value = resolve_raw_exact(parser.state, symbol)
    except Exception:
        return False
    return isinstance(value, (dict, list))


def state_get_direct_value(parser, symbol: str):
    return resolve_raw_exact(parser.state, symbol)


def read_resolved_value(parser, symbol: str):
    return resolve_raw_exact(parser.state, symbol)


def require_non_null(value: Any, symbol: str) -> Any:
    if value is None:
        raise ValueError(f"null symbol value: {symbol}")
    return value


def resolve_embedded_symbol_token(parser, token: str) -> str:
    validate_symbol(token, allow_bare_root=False, role="target")
    return expand_symbols_in_text(parser.state, token, max_passes=1)


def maybe_resolve_embedded_symbol_token(parser, token: str) -> Optional[str]:
    try:
        validate_symbol(token, allow_bare_root=False, role="target")
    except Exception:
        return None

    try:
        return resolve_embedded_symbol_token(parser, token)
    except Exception:
        return None


def expand_embedded_symbol_tokens_once(parser, text: str) -> str:
    return expand_symbols_in_text(parser.state, text, max_passes=1)


def expand_embedded_symbol_tokens(parser, text: str) -> str:
    return expand_symbols_in_text(parser.state, text, max_passes=16)


def resolve_direct_exec_symbol(parser, symbol: str) -> str:
    validate_symbol(symbol, allow_bare_root=False, role="target")

    root = symbol[0]
    if root not in ("$", "#", "&"):
        return symbol

    value = require_non_null(resolve_raw_exact(parser.state, symbol), symbol)
    if not isinstance(value, str):
        raise ValueError(f"direct command symbol must contain string value: {symbol}")
    return expand_symbols_in_text(parser.state, value, max_passes=16)


def maybe_expand_direct_exec_symbol(parser, line: str) -> str:
    raw = str(line or "").strip()
    if not raw or "=" in raw:
        return raw
    if raw[0] not in ("$", "#", "&"):
        return raw
    return resolve_direct_exec_symbol(parser, raw)


def is_single_bare_symbol_rhs(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if raw[0] not in ("$", "#", "&", "%", "!", "@", "|"):
        return False
    try:
        validate_symbol(raw, allow_bare_root=False, role="target")
    except Exception:
        return False
    return True


def resolve_assignment_rhs(parser, raw_value: str):
    text = str(raw_value or "").strip()

    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]

    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]

    if is_single_bare_symbol_rhs(text):
        return require_non_null(resolve_raw_exact(parser.state, text), text)

    return raw_value
