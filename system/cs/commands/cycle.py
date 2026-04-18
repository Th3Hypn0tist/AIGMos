# system/cs/commands/cycle.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from typing import Any, List

from system.runtime.runner import MODE_CYCLE, create_runner, ensure_worker
from system.runtime.runner_store import upsert_runner_def
from system.cs.state_ops import get_optional


command = "cycle"
help_short = 'cycle <source>'
help_full = """helper: create %name in cycle mode from &, $, or # source

rules:
- accepted sources: &name, $template, #table
- resolved snapshot must contain at least 2 steps
- runner name is derived from the source

note:
- cycle is outside the locked v40 canonical command surface
"""

def _dispatch_raw(parser, raw: str, cancel_event=None):
    err = parser.parse(raw)
    if err:
        raise RuntimeError(err)
    return None


def _state_get(parser, key: str) -> Any:
    return get_optional(parser.state, key)


def _sorted_indexed_values(node: Any) -> List[str]:
    if isinstance(node, list):
        return [str(x) for x in node]

    if isinstance(node, dict):
        items = []
        for key, value in node.items():
            try:
                index = int(key)
            except (TypeError, ValueError):
                raise ValueError(f"routine contains non-numeric key: {key!r}")
            items.append((index, str(value)))
        items.sort(key=lambda x: x[0])
        return [value for _, value in items]

    raise ValueError(
        f"resolved routine must be list or numeric-key dict, got: {type(node).__name__}"
    )


def _resolve_amp(parser, source: str) -> List[str]:
    node = _state_get(parser, source)
    return _sorted_indexed_values(node)


def _resolve_dollar(parser, source: str) -> List[str]:
    template = _state_get(parser, source)

    if not isinstance(template, str):
        raise ValueError(f"$ template must be string, got: {type(template).__name__}")

    parts = template.split()

    amp_tokens = [p for p in parts if p.startswith("&")]
    if not amp_tokens:
        raise ValueError("$ template must contain & source")
    if len(amp_tokens) > 1:
        raise ValueError("$ template supports exactly one & source")

    amp = amp_tokens[0]
    amp_lines = _resolve_amp(parser, amp)

    out = []
    for item in amp_lines:
        row_parts = [item if p == amp else p for p in parts]
        out.append(" ".join(row_parts))

    return out


def _resolve_hash(parser, source: str) -> list[str]:
    node = _state_get(parser, source)

    if not isinstance(node, dict):
        raise ValueError(f"# source must be dict, got: {type(node).__name__}")

    rows: list[tuple[int, object]] = []
    for key, value in node.items():
        try:
            idx = int(key)
        except (TypeError, ValueError):
            raise ValueError(f"# source contains non-numeric row key: {key!r}")
        rows.append((idx, value))

    rows.sort(key=lambda x: x[0])

    out: list[str] = []
    for idx, row in rows:
        expanded = _call_first(
            parser,
            (
                "resolve_hash_row",
                "expand_hash_row",
                "resolve_claim_row",
                "expand_claim_row",
            ),
            row,
        )

        if not isinstance(expanded, str):
            raise ValueError(
                f"# row {idx} must expand to one raw row string, got: {type(expanded).__name__}"
            )

        out.append(expanded)

    return out


def _resolve_source(parser, source: str) -> List[str]:
    if not source:
        raise ValueError("missing cycle source")

    root = source[0]

    if root == "&":
        lines = _resolve_amp(parser, source)
    elif root == "$":
        lines = _resolve_dollar(parser, source)
    elif root == "#":
        lines = _resolve_hash(parser, source)
    else:
        raise ValueError("cycle accepts only &, $, or # source")

    if len(lines) < 2:
        raise ValueError("cycle requires at least 2 steps")

    return lines


def _runner_name_from_source(source: str) -> str:
    return "%" + source[1:]


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error=str('usage: cycle <source>' or ""))

    source = parts[1].strip()

    if not source or source[0] not in "&$#":
        return HandlerResponse(error=str('cycle accepts only &, $, or # source' or ""))

    try:
        ensure_worker(
            lambda raw, cancel_event=None: _dispatch_raw(
                parser, raw, cancel_event=cancel_event
            )
        )

        lines = _resolve_source(parser, source)
        runner_name = _runner_name_from_source(source)

        runner = create_runner(
            source=source,
            lines=lines,
            mode=MODE_CYCLE,
            name=runner_name,
        )
        upsert_runner_def(
            parser.state,
            name=runner_name,
            source=source,
            mode=MODE_CYCLE,
            lines=lines,
            autostart=0,
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str(f"[ok] {runner['name']}" or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

