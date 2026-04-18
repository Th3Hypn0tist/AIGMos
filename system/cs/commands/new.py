
# system/cs/commands/new.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse

from system.cs.command_args import parse_argv
from system.cs.symbol_rules import require_layout_handle, require_route
from system.cs.runtime_ctx import get_ctx
from system.layout import definitions as layout_definitions

command = "new"
help_short = 'new |<instance> /<module-or-layout>'
help_full = """create one layout instance or one direct module instance

notes:
- /<name> first tries a layout template under system/library/layout or extensions/layout
- if no template exists, it falls back to direct module creation
- layout runtime state lives in the | symbol space

examples:
  new |Q /q
  new |HELP /help
  new |BUFFER /buffer
"""

def _normalize_instance_name(raw: str) -> str:
    name = require_layout_handle(raw, role="instance name")
    body = name[1:].strip()
    if "." in body:
        raise ValueError("new expects |<instance>, not |<module>.<instance>")
    if ':' in body:
        raise ValueError("new expects a layout instance handle, not a module handle")
    return body


def _normalize_route(raw: str) -> str:
    route = require_route(raw)
    body = route[1:].strip()
    if not body:
        raise ValueError("new expects /<module-or-layout>")
    return body


def handler(line: str, parser):
    try:
        _, instance_token, route_token = parse_argv(
            line,
            usage="usage: new |<instance> /<module-or-layout>",
            label="new",
            exact=2,
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        instance_name = _normalize_instance_name(instance_token)
        route_name = _normalize_route(route_token)

        from system.layout import registry as layout_registry  # type: ignore

        ctx = get_ctx(parser)

        try:
            tree = layout_definitions.parse_layout_definition(route_name)
        except Exception:
            tree = None

        if isinstance(tree, dict):
            specs = layout_definitions.flatten_module_specs(tree)
            bound = layout_registry.create_layout_binding(
                ctx,
                f"|{instance_name}",
                route_name,
                specs,
                tree=tree,
            )
            layout_registry.switch_active(ctx, f"|{instance_name}")
            return HandlerResponse(buffer_output=str(f'[ok] |{instance_name} -> /{route_name} ({len(bound)} modules)' or ""))

        module_name = route_name.lower()
        layout_registry.load_module(ctx, module_name)
        handle = f"|{instance_name}"
        config = {
            "instance_suffix": instance_name,
            **({"profile": "default" if instance_name.lower() == module_name else instance_name} if module_name == "q" else {}),
        }

        instance = layout_registry.create_instance(
            ctx,
            module_name,
            handle,
            config,
            start=True,
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str(f"[ok] {getattr(instance, 'handle', handle)}" or ""))


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
