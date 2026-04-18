from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from typing import Any, List

from system.cs.command_args import parse_tail
from system.cs.lib.ops import list_symbols
from system.cs.state_ops import get_optional, get_required


command = "run"
help_short = 'run <command|&source>'
help_full = """current implementation: execute one command directly or run one & routine once

rules:
- non-& input is dispatched as one raw command line
- & source is snapshotted and executed once in numeric order
- & routine must contain at least 1 step
- errors include failing step index and command

note:
- this help describes the current command implementation
"""

def _dispatch_raw(parser, raw: str):
    response = parser.parse(raw)
    if getattr(response, "error", None):
        raise RuntimeError(response.error)
    return response


def _state_get_value(parser, key: str) -> Any:
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
                raise ValueError(f"& routine contains non-numeric key: {key!r}")
            items.append((index, str(value)))
        items.sort(key=lambda x: x[0])
        return [value for _, value in items]

    raise ValueError(f"& routine must be list or numeric-key dict, got: {type(node).__name__}")


def _materialize_amp_from_children(parser, source: str) -> List[str]:
    prefix = source + ":"
    indexed = []

    for symbol in list_symbols(parser.state):
        if not symbol.startswith(prefix):
            continue

        rest = symbol[len(prefix):]
        if not rest:
            continue

        if ":" in rest:
            continue

        key = rest.strip()
        if key == "":
            continue

        try:
            index = int(key)
        except ValueError:
            raise ValueError(f"& routine contains non-numeric key: {key!r}")

        value = get_required(parser.state, f"{source}:{key}", message=f"& routine item is missing value: {source}:{key}")

        indexed.append((index, str(value)))

    indexed.sort(key=lambda x: x[0])
    return [value for _, value in indexed]


def _snapshot_amp(parser, source: str) -> List[str]:
    node = _state_get_value(parser, source)

    if node is not None:
        lines = _sorted_indexed_values(node)
    else:
        lines = _materialize_amp_from_children(parser, source)

    if len(lines) < 1:
        raise ValueError("run source must contain at least 1 step")

    return lines


def _run_lines_once(parser, lines: List[str]) -> None:
    for idx, raw in enumerate(lines):
        line = str(raw).strip()
        if line == "":
            continue
        try:
            _dispatch_raw(parser, line)
        except Exception as exc:
            raise RuntimeError(f"run step {idx} failed: {line} :: {exc}") from exc


def handler(line: str, parser) -> HandlerResponse:
    try:
        arg = parse_tail(line, usage="usage: run <command|source>")
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        if not arg.startswith("&"):
            _dispatch_raw(parser, arg)
            return HandlerResponse()

        lines = _snapshot_amp(parser, arg)
        _run_lines_once(parser, lines)
        return HandlerResponse()

    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

