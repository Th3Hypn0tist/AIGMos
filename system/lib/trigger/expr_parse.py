from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LOGIC_WORDS = {'AND', 'OR', 'XOR', 'NOT'}
COMPARE_OPS = {'==', '!=', '<', '<=', '>', '>='}
SIGILS = '$#&%@!|'


@dataclass(frozen=True, slots=True)
class ExprToken:
    kind: str
    value: str
    pos: int


class _TokenStream:
    def __init__(self, tokens: list[ExprToken]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> ExprToken | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def next(self) -> ExprToken:
        token = self.peek()
        if token is None:
            raise ValueError('unexpected end of expression')
        self.index += 1
        return token

    def expect(self, kind: str, value: str | None = None) -> ExprToken:
        token = self.next()
        if token.kind != kind:
            raise ValueError(f'expected {kind}, got {token.kind}')
        if value is not None and token.value != value:
            raise ValueError(f'expected {value}, got {token.value}')
        return token

    def at_end(self) -> bool:
        return self.peek() is None


def tokenize_expr(text: str) -> list[ExprToken]:
    raw = str(text or '').strip()
    if not raw:
        raise ValueError('expression cannot be empty')

    out: list[ExprToken] = []
    i = 0
    n = len(raw)

    while i < n:
        ch = raw[i]
        if ch.isspace():
            i += 1
            continue

        if ch == '(':
            out.append(ExprToken('LPAREN', ch, i))
            i += 1
            continue
        if ch == ')':
            out.append(ExprToken('RPAREN', ch, i))
            i += 1
            continue

        two = raw[i:i + 2]
        if two in {'==', '!=', '<=', '>='}:
            out.append(ExprToken('OP', two, i))
            i += 2
            continue
        if ch in {'<', '>'}:
            out.append(ExprToken('OP', ch, i))
            i += 1
            continue

        if ch in {'"', "'"}:
            value, i = _read_quoted(raw, i)
            out.append(ExprToken('LITERAL', value, i))
            continue

        start = i
        while i < n and (not raw[i].isspace()) and raw[i] not in '()<>!=':
            i += 1
        value = raw[start:i]
        if not value:
            raise ValueError(f'unexpected token at {start}')

        upper = value.upper()
        if upper in LOGIC_WORDS:
            out.append(ExprToken('LOGIC', upper, start))
        elif value[0] in SIGILS:
            out.append(ExprToken('REF', value, start))
        else:
            out.append(ExprToken('LITERAL', value, start))

    return out


def parse_expr(text: str, *, strict_grouping: bool = True) -> dict[str, Any]:
    tokens = tokenize_expr(text)
    if strict_grouping:
        _validate_canonical_grouping(tokens)
    stream = _TokenStream(tokens)
    node = parse_logic(stream)
    if not stream.at_end():
        token = stream.peek()
        raise ValueError(f'unexpected trailing token: {token.value if token else "<eof>"}')
    return node


def parse_logic(stream: _TokenStream) -> dict[str, Any]:
    node = parse_and(stream)
    while True:
        token = stream.peek()
        if token is None or token.kind != 'LOGIC' or token.value not in {'OR', 'XOR'}:
            return node
        op = stream.next().value
        right = parse_and(stream)
        node = {'type': 'logic', 'op': op, 'left': node, 'right': right}


def parse_and(stream: _TokenStream) -> dict[str, Any]:
    node = parse_unary(stream)
    while True:
        token = stream.peek()
        if token is None or token.kind != 'LOGIC' or token.value != 'AND':
            return node
        stream.next()
        right = parse_unary(stream)
        node = {'type': 'logic', 'op': 'AND', 'left': node, 'right': right}


def parse_unary(stream: _TokenStream) -> dict[str, Any]:
    token = stream.peek()
    if token is not None and token.kind == 'LOGIC' and token.value == 'NOT':
        stream.next()
        node = parse_unary(stream)
        return {'type': 'not', 'node': node}
    return parse_group(stream)


def parse_group(stream: _TokenStream) -> dict[str, Any]:
    token = stream.peek()
    if token is not None and token.kind == 'LPAREN':
        stream.next()
        node = parse_logic(stream)
        stream.expect('RPAREN')
        return node
    return parse_compare(stream)


def parse_compare(stream: _TokenStream) -> dict[str, Any]:
    left = _parse_value_token(stream.next())
    op = stream.next()
    if op.kind != 'OP' or op.value not in COMPARE_OPS:
        raise ValueError(f'expected comparison operator after {left["value"]}')
    right = _parse_value_token(stream.next())
    return {
        'type': 'compare',
        'op': op.value,
        'left': left,
        'right': right,
    }


def _parse_value_token(token: ExprToken) -> dict[str, str]:
    if token.kind not in {'REF', 'LITERAL'}:
        raise ValueError(f'expected value token, got {token.kind}')
    return {'kind': token.kind.lower(), 'value': token.value}


def _validate_canonical_grouping(tokens: list[ExprToken]) -> None:
    has_logic = any(token.kind == 'LOGIC' for token in tokens)
    if not has_logic:
        return
    has_parens = any(token.kind in {'LPAREN', 'RPAREN'} for token in tokens)
    if not has_parens:
        raise ValueError('logical expressions must be grouped with parentheses')


def _read_quoted(text: str, start: int) -> tuple[str, int]:
    quote = text[start]
    i = start + 1
    buf: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == '\\':
            i += 1
            if i >= len(text):
                raise ValueError('unterminated escape in quoted string')
            buf.append(text[i])
            i += 1
            continue
        if ch == quote:
            return ''.join(buf), i + 1
        buf.append(ch)
        i += 1
    raise ValueError('unterminated quoted string')
