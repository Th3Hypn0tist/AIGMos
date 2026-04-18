from __future__ import annotations

from typing import Any, List

from system.cs.parser import HandlerResponse
from system.runtime.runner import MODE_ONCE, create_runner, ensure_worker


command = "run"
help_short = "run <command|source>"
help_full = (
    "run <command|source>\n"
    "\n"
    "Semantics:\n"
    "- run <single command> -> direct execute, no runner instance\n"
    "- run &name            -> snapshot indexed & routine, create live %name, mode=once\n"
    "\n"
    "Rules:\n"
    "- run uses mode=once always\n"
    "- & routine must resolve to at least 1 step\n"
    "- runner name is derived from source: &foo -> %foo\n"
    "- run never writes persistent runner definitions\n"
)


def _dispatch_raw(parser, raw: str, cancel_event=None):
    err = parser.parse(raw)
    if err:
        raise RuntimeError(err)
    return None


def _state_get_value(parser, key: str) -> Any:
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
    node = _state_get_value(parser, source)
    lines = _sorted_indexed_values(node)

    if len(lines) < 1:
        raise ValueError("run source must contain at least 1 step")

    return lines


def _runner_name_from_source(source: str) -> str:
    if not source.startswith("&"):
        raise ValueError(f"run source must start with &: {source!r}")
    return "%" + source[1:]


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return HandlerResponse(error="usage: run <command|source>")

    arg = parts[1].strip()
    if not arg:
        return HandlerResponse(error="usage: run <command|source>")

    if not arg.startswith("&"):
        try:
            _dispatch_raw(parser, arg)
        except Exception as exc:
            return HandlerResponse(error=str(exc))
        return HandlerResponse()

    source = arg

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
            mode=MODE_ONCE,
            name=runner_name,
        )
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output=f"[ok] {runner['name']}")
