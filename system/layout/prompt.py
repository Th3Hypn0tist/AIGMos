from __future__ import annotations

import re
from typing import Any

from system.cs.runtime_ctx import get_ctx, get_layout_caller_handle
from system.lib.symbols import (
    SymbolError,
    expand_text_recursive_with_token_resolver,
    expand_text_with_token_resolver,
    is_symbol_ref,
    resolve_raw_exact,
)

_SEGMENT_RE = r"[A-Za-z0-9._-]+"
_TOKEN_BODY_RE = rf"(?:\|:(?:{_SEGMENT_RE})(?::{_SEGMENT_RE})*|\|{_SEGMENT_RE}(?::{_SEGMENT_RE})+|[\$#&%!@|][A-Za-z0-9._]+(?::[A-Za-z0-9._]+)*)"
_PROMPT_SYMBOL_RE = re.compile(rf"({_TOKEN_BODY_RE})")
_PROMPT_BRACKET_SYMBOL_RE = re.compile(rf"\[({_TOKEN_BODY_RE})\]")


def _resolve_layout_prompt_value(parser, token: str) -> tuple[bool, Any]:
    raw = str(token or "").strip()
    if not raw.startswith("|") or ":" not in raw:
        return False, raw

    ctx = get_ctx(parser)
    if not isinstance(ctx, dict) or not ctx:
        return False, raw

    from system.layout import registry as layout_registry
    from system.layout import state as layout_state

    if raw == "|:handle":
        handle = str(get_layout_caller_handle(parser) or "").strip()
        return (bool(handle), handle or raw)

    if raw.startswith("|:"):
        handle = str(get_layout_caller_handle(parser) or "").strip()
        if not handle:
            return False, raw
        key = raw[2:]
        if not key:
            return False, raw
        if key == "handle":
            return True, handle
        meta = layout_state.get_meta(ctx, handle, key, None)
        if meta is not None:
            return True, meta
        value = layout_state.get_value(ctx, f"{handle}:{key}", None)
        return (value is not None, value if value is not None else raw)

    owner, key = raw.split(":", 1)
    if not key:
        return False, raw
    try:
        owner_handle = layout_registry.normalize_handle(owner)
    except Exception:
        return False, raw
    if key == "handle":
        return True, owner_handle
    meta = layout_state.get_meta(ctx, owner_handle, key, None)
    if meta is not None:
        return True, meta
    value = layout_state.get_value(ctx, f"{owner_handle}:{key}", None)
    return (value is not None, value if value is not None else raw)


def _resolve_prompt_value(parser, token: str) -> tuple[bool, Any]:
    raw = str(token or "").strip()
    if raw.startswith("|") and ":" in raw:
        found, value = _resolve_layout_prompt_value(parser, raw)
        if found:
            return True, value
    value = resolve_raw_exact(parser.state, raw)
    return (value is not None, value)


def expand_prompt_symbols(
    parser,
    text: str,
    *,
    mode: str = "normal_inline",
    strict: bool | None = None,
    max_passes: int = 16,
) -> str:
    current_mode = str(mode or "normal_inline").strip().lower()
    if current_mode == "system_recursive":
        return expand_text_recursive_with_token_resolver(
            text,
            plain_pattern=_PROMPT_SYMBOL_RE,
            bracket_pattern=_PROMPT_BRACKET_SYMBOL_RE,
            resolve_token=lambda token: _resolve_prompt_value(parser, token),
            strict=True if strict is None else bool(strict),
            max_passes=max_passes,
        )

    return expand_text_with_token_resolver(
        text,
        plain_pattern=_PROMPT_SYMBOL_RE,
        bracket_pattern=_PROMPT_BRACKET_SYMBOL_RE,
        resolve_token=lambda token: _resolve_prompt_value(parser, token),
        strict=False if strict is None else bool(strict),
        max_bracket_passes=max_passes,
    )


def expand_prompt_tokens(parser, tokens: list[str], *, mode: str = "normal_inline", strict: bool | None = None, max_passes: int = 16) -> str:
    return expand_prompt_symbols(
        parser,
        " ".join(str(token) for token in tokens).strip(),
        mode=mode,
        strict=strict,
        max_passes=max_passes,
    )


__all__ = [
    "expand_prompt_symbols",
    "expand_prompt_tokens",
    "is_symbol_ref",
    "resolve_raw_exact",
    "SymbolError",
]
