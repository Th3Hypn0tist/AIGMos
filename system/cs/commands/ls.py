from __future__ import annotations

from system.cs.lib.ops import PRIMITIVE_HELP, list_symbols, validate_symbol, wildcard_prefix_match
from system.cs.parser import HandlerResponse

command = "ls"
help_short = "ls [target|prefix*]"
help_full = "list primitives, roots, direct children, wildcard matches, runtime triggers, or runtime events"


def handler(line: str, parser) -> HandlerResponse:
    parts = line.split(maxsplit=1)
    if len(parts) == 1:
        rows = [f"{root}  {text}" for root, text in PRIMITIVE_HELP.items()]
        return HandlerResponse(buffer_output="\n".join(rows))

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error="usage: ls [target|prefix*]")

    if target == "!":
        triggers = parser.runtime.get("triggers")
        if triggers is None or not hasattr(triggers, "list_names"):
            return HandlerResponse(buffer_output="")
        return HandlerResponse(buffer_output="\n".join(triggers.list_names()))

    if target == "@":
        events = parser.runtime.get("events")
        if events is None or not hasattr(events, "list_events"):
            return HandlerResponse(buffer_output="")
        return HandlerResponse(buffer_output="\n".join(events.list_events()))

    if target.endswith("*"):
        try:
            rows = wildcard_prefix_match(parser.state, target)
        except ValueError as exc:
            return HandlerResponse(error=str(exc))
        return HandlerResponse(buffer_output="\n".join(rows))

    try:
        validate_symbol(target, allow_bare_root=True)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))

    try:
        if len(target) == 1:
            rows = _list_root_children(parser.state, target)
        else:
            rows = _list_direct_children(parser.state, target)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="\n".join(rows))


def _list_root_children(state, root: str) -> list[str]:
    sep = ":" if root == "#" else "."
    names = set()

    for symbol in list_symbols(state):
        if not symbol.startswith(root):
            continue

        rest = symbol[len(root):]
        if not rest:
            continue

        child = rest.split(sep, 1)[0]
        if child:
            names.add(child)

    return sorted(names)


def _list_direct_children(state, target: str) -> list[str]:
    root = target[0]

    if root == "&":
        value = state.get(target)
        if value["error"]:
            raise ValueError(value["error"])
        result = value["result"]
        if result is None:
            raise ValueError("target not found")
        if isinstance(result, list):
            return [str(i) for i in range(len(result))]
        if isinstance(result, dict):
            return sorted(str(k) for k in result.keys())
        return []

    sep = ":" if root == "#" else "."
    prefix = target + sep
    names = set()

    for symbol in list_symbols(state):
        if not symbol.startswith(prefix):
            continue

        rest = symbol[len(prefix):]
        if not rest:
            continue

        child = rest.split(sep, 1)[0]
        if child:
            names.add(child)

    direct_value = state.get(target)
    if direct_value["error"]:
        raise ValueError(direct_value["error"])
    if direct_value["result"] is None and not names:
        raise ValueError("target not found")

    return sorted(names)
