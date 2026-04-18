from __future__ import annotations

import shlex
from typing import Optional


def parse_argv(
    line: str,
    *,
    usage: str,
    label: Optional[str] = None,
    exact: int | None = None,
    min_args: int | None = None,
    max_args: int | None = None,
) -> list[str]:
    try:
        parts = shlex.split(str(line or ""))
    except Exception as exc:
        prefix = f"{label} parse error" if label else "parse error"
        raise ValueError(f"{prefix}: {exc}") from exc

    argc = max(0, len(parts) - 1)

    if exact is not None and argc != exact:
        raise ValueError(usage)
    if min_args is not None and argc < min_args:
        raise ValueError(usage)
    if max_args is not None and argc > max_args:
        raise ValueError(usage)

    return parts


def parse_tail(line: str, *, usage: str) -> str:
    parts = str(line or "").split(maxsplit=1)
    if len(parts) != 2:
        raise ValueError(usage)

    tail = str(parts[1] or "").strip()
    if not tail:
        raise ValueError(usage)
    return tail


def _consume_nonspace_token(raw: str, start: int) -> tuple[str, int]:
    i = int(start)
    n = len(raw)
    while i < n and raw[i].isspace():
        i += 1
    begin = i
    while i < n and not raw[i].isspace():
        i += 1
    return raw[begin:i], i


def _consume_whitespace(raw: str, start: int) -> int:
    i = int(start)
    n = len(raw)
    while i < n and raw[i].isspace():
        i += 1
    return i


def parse_command_tail_raw(line: str, *, usage: str, label: Optional[str] = None) -> tuple[str, str]:
    raw = str(line or "")
    command, pos = _consume_nonspace_token(raw, 0)
    if not command:
        raise ValueError(usage)
    tail_start = _consume_whitespace(raw, pos)
    tail = raw[tail_start:]
    if not tail or not tail.strip():
        if label:
            raise ValueError(f"{label} requires prompt")
        raise ValueError(usage)
    return command, tail


def parse_command_output_tail_raw(line: str, *, usage: str, label: Optional[str] = None) -> tuple[str, str, str]:
    raw = str(line or "")
    command, pos = _consume_nonspace_token(raw, 0)
    if not command:
        raise ValueError(usage)
    pos = _consume_whitespace(raw, pos)
    output_symbol, pos = _consume_nonspace_token(raw, pos)
    if not output_symbol:
        raise ValueError(usage)
    tail_start = _consume_whitespace(raw, pos)
    tail = raw[tail_start:]
    if not tail or not tail.strip():
        if label:
            raise ValueError(f"{label} requires prompt")
        raise ValueError(usage)
    return command, output_symbol, tail
