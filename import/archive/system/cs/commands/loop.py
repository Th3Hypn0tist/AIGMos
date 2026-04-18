# system/cs/commands/loop.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from system.runtime.runner import MODE_LOOP, create_runner, ensure_worker
from system.runtime.runner_store import upsert_runner_def


@dataclass
class HandlerResponse:
    result: object = None
    buffer_output: str = ""
    error: str = ""


command = "loop"
help_short = "loop &name -> create %name in loop mode"
help_full = (
    "loop &name\n"
    "Create a loop runner from indexed & routine.\n"
    "Rules:\n"
    "- accepts only & sources\n"
    "- snapshot must contain at least 2 rows\n"
)


def _dispatch_raw(parser, raw: str, cancel_event=None):
    err = parser.parse(raw)
    if err:
        raise RuntimeError(err)
    return None


def _state_get(parser, key: str) -> Any:
    out = parser.state.get(key)
    if out["error"]:
        raise ValueError(out["error"])
    return out["result"]


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


def _snapshot_amp(parser, source: str) -> List[str]:
    node = _state_get(parser, source)
    lines = _sorted_indexed_values(node)

    if len(lines) < 2:
        raise ValueError("loop requires at least 2 steps")

    return lines


def _runner_name_from_source(source: str) -> str:
    return "%" + source[1:]


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: loop &name")

    source = parts[1].strip()

    if not source.startswith("&"):
        return HandlerResponse(error="loop accepts only & source")

    try:
        ensure_worker(
            lambda raw, cancel_event=None: _dispatch_raw(
                parser, raw, cancel_event=cancel_event
            )
        )

        lines = _snapshot_amp(parser, source)
        runner_name = _runner_name_from_source(source)

        runner = create_runner(
            source=source,
            lines=lines,
            mode=MODE_LOOP,
            name=runner_name,
        )
        upsert_runner_def(
            parser.state,
            name=runner_name,
            source=source,
            mode=MODE_LOOP,
            lines=lines,
            autostart=0,
        )
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output=f"[ok] {runner['name']}")
