from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.lib.ops import PRIMITIVE_HELP, list_symbols, wildcard_prefix_match
from system.cs.symbol_rules import require_layout_handle, require_symbol
from system.cs.runtime_ctx import get_ctx, get_events, get_triggers

command = "ls"
help_short = 'ls [target|prefix*]'
help_full = """list roots, direct children, wildcard matches, or selected runtime objects

examples:
  ls
  ls $foo
  ls $foo*
  ls |

notes:
- ls | lists top-level layout instances
- ls ! and ls @ list trigger and event objects
"""

def handler(line: str, parser):
    parts = line.split(maxsplit=1)
    if len(parts) == 1:
        rows = [f"{root}  {text}" for root, text in PRIMITIVE_HELP.items()]
        return HandlerResponse(buffer_output=str("\n".join(rows) or ""))

    target = parts[1].strip()
    if not target:
        return HandlerResponse(error=str("usage: ls [target|prefix*]" or ""))

    if target == "!":
        return HandlerResponse(buffer_output=str("\n".join(_list_trigger_names(parser)) or ""))

    if target.startswith("!"):
        return HandlerResponse(error=str("target not listable" or ""))

    if target == "@":
        return HandlerResponse(buffer_output=str("\n".join(_list_event_names(parser)) or ""))

    if target.startswith("@"):
        return HandlerResponse(error=str("target not listable" or ""))

    if target.startswith("|"):
        try:
            if target != "|" and ":" in target[1:]:
                rows = _list_direct_children(parser.state, target)
            else:
                rows = _list_layout_children(target, parser)
        except ValueError as exc:
            return HandlerResponse(error=str(str(exc) or ""))
        return HandlerResponse(buffer_output=str("\n".join(rows) or ""))

    if target.endswith("*"):
        try:
            rows = wildcard_prefix_match(parser.state, target)
        except ValueError as exc:
            return HandlerResponse(error=str(str(exc) or ""))
        return HandlerResponse(buffer_output=str("\n".join(rows) or ""))

    try:
        require_symbol(target, allow_bare_root=True)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        if len(target) == 1:
            rows = _list_root_children(parser.state, target)
        else:
            rows = _list_direct_children(parser.state, target)
    except ValueError as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str("\n".join(rows) or ""))


def _normalize_layout_handle(raw: str) -> str:
    text = require_layout_handle(raw)
    body = text[1:].strip()

    if "." in body:
        prefix, suffix = body.split(".", 1)
        prefix = prefix.strip().upper()
        suffix = suffix.strip()
        if not prefix:
            raise ValueError("layout handle prefix cannot be empty")
        return f"|{prefix}.{suffix}" if suffix else f"|{prefix}"

    prefix = body.strip().upper()
    if not prefix:
        raise ValueError("layout handle prefix cannot be empty")
    return f"|{prefix}"


def _list_trigger_names(parser) -> list[str]:
    triggers = get_triggers(parser)
    if triggers is None or not hasattr(triggers, "list_names"):
        return []
    return [f"!{name}" for name in triggers.list_names()]


def _list_event_names(parser) -> list[str]:
    events = get_events(parser)
    if events is None or not hasattr(events, "list_events"):
        return []
    return [f"@{name}" for name in events.list_events()]


def _known_layout_handles(parser) -> list[str]:
    from system.layout import registry as layout_registry  # type: ignore

    ctx = get_ctx(parser)
    layout_registry.bootstrap(ctx)

    handles = set()
    for handle in layout_registry.list_instances(ctx):
        parent = layout_registry.get_parent_layout_for_instance(ctx, handle)
        if parent:
            handles.add(parent)
        else:
            handles.add(handle)

    return sorted(handles, key=lambda item: item[1:])


def _layout_direct_meta_fields(ctx, handle: str) -> list[str]:
    from system.layout import state as layout_state  # type: ignore

    prefix = layout_state.meta_prefix(handle)
    names: set[str] = set()

    for symbol in list_symbols(ctx["state"]):
        if symbol == prefix:
            continue
        child = _state_direct_child_name(symbol, prefix)
        if child:
            names.add(child)

    return sorted(names)


def _list_layout_children(target: str, parser) -> list[str]:
    from system.layout import registry as layout_registry  # type: ignore

    ctx = get_ctx(parser)
    if target == "|":
        # Show only top-level layout handles.
        # Internal bound module instances like |CS.Q.cs1 must not leak into ls |.
        return [handle[1:] for handle in _known_layout_handles(parser)]

    clean = _normalize_layout_handle(target)
    known_roots = _known_layout_handles(parser)

    if layout_registry.has_layout_binding(ctx, clean):
        rows = [child[1:] for child in layout_registry.get_bound_layout_modules(ctx, clean)]
        if rows:
            return rows
        fields = _layout_direct_meta_fields(ctx, clean)
        if fields:
            return fields
        return []

    if layout_registry.has_instance(ctx, clean):
        fields = _layout_direct_meta_fields(ctx, clean)
        if fields:
            return fields
        return []

    children = sorted(handle[1:] for handle in known_roots if handle.startswith(clean + "."))
    if children:
        return children

    raise ValueError("target not found")


def _first_segment(text: str) -> str:
    clean = str(text or "").strip()
    if not clean:
        return ""

    # Child segments are separated only by ":".
    # "." is valid inside a symbol segment (for example file names like
    # "README.md") and must not be treated as structure by ls.
    idx = clean.find(":")
    if idx == -1:
        return clean

    return clean[:idx].strip()


def _state_direct_child_name(symbol: str, prefix: str) -> str | None:
    if symbol == prefix:
        return None
    if not symbol.startswith(prefix):
        return None

    rest = symbol[len(prefix):]
    if not rest:
        return None

    if not rest.startswith(":") and not rest.startswith("."):
        return None

    child = _first_segment(rest[1:])
    return child or None


def _list_root_children(state, root: str) -> list[str]:
    names = set()

    for symbol in list_symbols(state):
        if not symbol.startswith(root):
            continue

        body = symbol[1:].strip()
        if not body:
            continue

        child = _first_segment(body)
        if child:
            names.add(child)

    return sorted(names)


def _list_direct_children(state, target: str) -> list[str]:
    names = set()

    for symbol in list_symbols(state):
        child = _state_direct_child_name(symbol, target)
        if child:
            names.add(child)

    if names:
        return sorted(names)

    for symbol in list_symbols(state):
        if symbol == target:
            return []

    raise ValueError("target not found")


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
