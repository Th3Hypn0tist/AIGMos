from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from datetime import datetime

from system.boot import GREETING_TEXT
from system.lib.q.profile import set_active_profile
from system.lib.q.transport import health_q_profile
from system.cs.runtime_ctx import (
    force_render,
    get_ctx,
    get_layout_caller_handle,
    set_flag,
    set_running,
)

command = "/"
help_short = '/help [/cmd] | /time | /greeting | /clear | /health q[.alias] | /exit'
help_full = """local slash command surface

subcommands:
- /help [cmd]      list short help or one full help
- /time            print local time to buffer
- /greeting        print greeting
- /clear           clear current layout modules and queue redraw
- /cs              switch active layout to cs template instance
- /q               switch active layout to q template instance
- /monitor[.alias] switch active layout to monitor instance
- /health q[.x]    GET q profile health_url
- /exit            stop app
"""

SLASH_HELP = {
    "/help": "/help [cmd] -> list short help or one full help",
    "/time": "/time -> print local time to buffer",
    "/exit": "/exit -> stop app",
    "/greeting": "/greeting -> print greeting",
    "/clear": "/clear -> call clear() on clearable modules in the current layout instance and queue hard terminal redraw",
    "/cs": "/cs -> switch active layout to cs template instance",
    "/q": "/q -> switch active layout to q template instance",
    "/monitor": "/monitor[.<alias>] -> switch active layout to monitor instance",
    "/health": "/health q[.<alias>] -> GET q profile health_url",
}



def _queue_hard_redraw(parser) -> None:
    try:
        from system.layout import terminal as layout_terminal  # type: ignore

        ctx = get_ctx(parser)
        if isinstance(ctx, dict):
            layout_terminal.queue_hard_redraw(ctx)
    except Exception:
        pass


def _force_hard_render(parser) -> None:
    _queue_hard_redraw(parser)
    force_render(parser)


def _resolve_q_alias(token: str) -> str:
    if "." not in token:
        return "default"
    return token.split(".", 1)[1].strip() or "default"


def _switch_layout(parser, route: str) -> None:
    from system.layout import registry as layout_registry  # type: ignore

    ctx = get_ctx(parser)
    resolved = layout_registry.ensure_instance(ctx, route)
    handle = getattr(resolved, "handle", resolved)
    layout_registry.switch_active(ctx, str(handle))


def _clear_current_layout_modules(parser) -> list[str]:
    from system.layout import registry as layout_registry  # type: ignore

    ctx = get_ctx(parser)
    handle = get_layout_caller_handle(parser)
    return layout_registry.clear_layout_modules(ctx, handle or None)



def handler(line: str, parser):
    tokens = line.split()
    subcmd = tokens[0].lower()

    if subcmd == "/help":
        if len(tokens) == 1:
            items = []
            for name, short in parser.get_short_help().items():
                items.append(short if name == "/" else f"{name} -> {short}")
            return HandlerResponse(buffer_output=str('\n'.join(items) or ""))

        target = tokens[1]
        if target.startswith("/"):
            text = SLASH_HELP.get(target, "")
            if text:
                return HandlerResponse(buffer_output=str(text or ""))

        text = parser.get_full_help(target)
        if not text:
            return HandlerResponse(error=str(f'help not found: {target}' or ""))
        return HandlerResponse(buffer_output=str(text or ""))

    if subcmd == "/time":
        return HandlerResponse(buffer_output=str(datetime.now().strftime('%Y-%m-%d %H:%M:%S') or ""))

    if subcmd == "/exit":
        parser.should_exit = True
        set_running(parser, False)
        set_flag(parser, "force_render", True)
        return HandlerResponse(buffer_output=str('[ok] exit' or ""))

    if subcmd == "/greeting":
        return HandlerResponse(buffer_output=str(GREETING_TEXT or ""))

    if subcmd == "/clear":
        try:
            _clear_current_layout_modules(parser)
        except Exception as exc:
            return HandlerResponse(error=str(str(exc) or ""))

        _force_hard_render(parser)
        return HandlerResponse()

    if subcmd == "/monitor" or subcmd.startswith("/monitor."):
        try:
            route = "/monitor" + (subcmd[len("/monitor"):] if subcmd.startswith("/monitor.") else "")
            _switch_layout(parser, route)
        except Exception as exc:
            return HandlerResponse(error=str(str(exc) or ""))
        force_render(parser)
        return HandlerResponse()

    if subcmd == "/q" or subcmd.startswith("/q."):
        if len(tokens) != 1:
            return HandlerResponse(error=str('usage: /q[.<alias>]' or ""))

        alias = _resolve_q_alias(subcmd)
        try:
            set_active_profile(parser, alias)
            _switch_layout(parser, subcmd)
        except Exception as exc:
            return HandlerResponse(error=str(str(exc) or ""))
        force_render(parser)
        return HandlerResponse()

    if subcmd == "/health":
        if len(tokens) != 2:
            return HandlerResponse(error=str('usage: /health q[.<alias>]' or ""))

        target = tokens[1].lower()
        if not (target == "q" or target.startswith("q.")):
            return HandlerResponse(error=str('usage: /health q[.<alias>]' or ""))

        try:
            alias = _resolve_q_alias(target)
            return HandlerResponse(buffer_output=str(health_q_profile(parser, alias) or ""))
        except Exception as exc:
            return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(error=str(f'unknown slash command: {subcmd}' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

