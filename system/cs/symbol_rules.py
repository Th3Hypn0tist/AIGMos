from __future__ import annotations

from typing import Iterable, Sequence

from system.lib.symbols import validate_symbol


_SYMBOL_LABELS = {
    '$': '$ symbol',
    '#': '# symbol',
    '&': '& symbol',
    '%': '% symbol',
    '!': '! symbol',
    '@': '@ symbol',
    '|': '| symbol',
}


def _normalize_allowed(allowed: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(allowed, str):
        return tuple(ch for ch in allowed if ch)
    return tuple(str(ch) for ch in allowed if str(ch))


def _join_roots(roots: Sequence[str]) -> str:
    if not roots:
        return ''
    if len(roots) == 1:
        return roots[0]
    if len(roots) == 2:
        return f"{roots[0]} or {roots[1]}"
    return ", ".join(roots[:-1]) + f", or {roots[-1]}"


def require_symbol(symbol: str, *, allowed: Iterable[str] | str | None = None, allow_bare_root: bool = False, role: str = 'target') -> str:
    root = validate_symbol(symbol, allow_bare_root=allow_bare_root)

    if allowed is None:
        return root

    allowed_roots = _normalize_allowed(allowed)
    if root in allowed_roots:
        return root

    if len(allowed_roots) == 1:
        raise ValueError(f"{role} must be a {_SYMBOL_LABELS.get(allowed_roots[0], allowed_roots[0])}")

    raise ValueError(f"{role} must start with {_join_roots(allowed_roots)}")


def require_prefixed_token(token: str, prefix: str, *, role: str) -> str:
    text = str(token or '').strip()
    if not text.startswith(prefix) or len(text) == 1:
        raise ValueError(f"{role} must start with {prefix}")
    return text


def require_route(token: str, *, role: str = 'route') -> str:
    text = str(token or '').strip()
    if not text.startswith('/'):
        raise ValueError(f"{role} must start with /")
    if len(text) == 1:
        raise ValueError(f"{role} cannot be empty")
    return text


def require_layout_handle(token: str, *, role: str = 'layout handle') -> str:
    text = str(token or '').strip()
    if not text.startswith('|'):
        raise ValueError(f"{role} must start with |")
    if len(text) == 1:
        raise ValueError(f"{role} cannot be empty")
    return text
