from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from system.lib.trigger.expr_parse import parse_expr

MISSING = object()
_NUMERIC_RE = re.compile(r'^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$')
Resolver = Callable[[str], Any]


def eval_expr(text: str, resolver: Resolver, *, strict_grouping: bool = True) -> bool:
    ast = parse_expr(text, strict_grouping=strict_grouping)
    return bool(eval_expr_ast(ast, resolver))


def eval_expr_ast(ast: dict[str, Any], resolver: Resolver) -> bool:
    node_type = str(ast.get('type') or '').strip()
    if node_type == 'compare':
        left = resolve_token(ast.get('left'), resolver)
        right = resolve_token(ast.get('right'), resolver)
        return eval_compare(left, str(ast.get('op') or ''), right)
    if node_type == 'logic':
        left = bool(eval_expr_ast(ast.get('left') or {}, resolver))
        right = bool(eval_expr_ast(ast.get('right') or {}, resolver))
        return eval_logic(str(ast.get('op') or ''), left, right)
    if node_type == 'not':
        return eval_not(bool(eval_expr_ast(ast.get('node') or {}, resolver)))
    raise ValueError(f'unknown expression node type: {node_type}')


def eval_compare(left: Any, op: str, right: Any) -> bool:
    if left is MISSING or right is MISSING:
        return False

    left_text = normalize_canonical_value(left)
    right_text = normalize_canonical_value(right)

    if op == '==':
        return left_text == right_text
    if op == '!=':
        return left_text != right_text

    left_num = _try_decimal(left_text)
    right_num = _try_decimal(right_text)
    if left_num is not None and right_num is not None:
        return _compare_ordered(left_num, op, right_num)
    return _compare_ordered(left_text, op, right_text)


def eval_logic(op: str, left: bool, right: bool) -> bool:
    if op == 'AND':
        return bool(left and right)
    if op == 'OR':
        return bool(left or right)
    if op == 'XOR':
        return bool(bool(left) ^ bool(right))
    raise ValueError(f'unsupported logical operator: {op}')


def eval_not(node_value: bool) -> bool:
    return not bool(node_value)


def resolve_token(token: dict[str, Any] | None, resolver: Resolver) -> Any:
    token = token if isinstance(token, dict) else {}
    kind = str(token.get('kind') or '').strip().lower()
    value = str(token.get('value') or '')

    if kind == 'ref':
        try:
            resolved = resolver(value)
        except Exception:
            return MISSING
        return MISSING if resolved is None else resolved

    if kind == 'literal':
        return value

    raise ValueError(f'unsupported token kind: {kind}')


def normalize_canonical_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return ''
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return str(value)


def _try_decimal(text: str) -> Decimal | None:
    raw = str(text or '').strip()
    if not raw or not _NUMERIC_RE.fullmatch(raw):
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _compare_ordered(left: Any, op: str, right: Any) -> bool:
    if op == '<':
        return left < right
    if op == '<=':
        return left <= right
    if op == '>':
        return left > right
    if op == '>=':
        return left >= right
    raise ValueError(f'unsupported comparison operator: {op}')
