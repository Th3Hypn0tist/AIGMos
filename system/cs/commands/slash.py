# system/cs/commands/slash.py

from __future__ import annotations

from datetime import datetime

from system.boot import GREETING_TEXT
from system.config import load_config
from system.cs.lib.qcall import health_q_profile, set_active_profile
from system.cs.parser import HandlerResponse

command = "/"
help_short = "/help /time /exit /greeting /clear /reload /q /buffer /health"
help_full = "slash commands"


SLASH_HELP = {
    "/help": "/help [cmd] -> list short help or one full help",
    "/time": "/time -> print local time to buffer",
    "/exit": "/exit -> stop app",
    "/greeting": "/greeting -> print greeting",
    "/clear": "/clear -> clear $SYSTEM.BUFFER",
    "/reload": "/reload -> reload config.json into runtime and #SYSTEM:config:*",
    "/q": "/q[.<alias>] -> set q layout, set active q profile/chat, force rerender",
    "/buffer": "/buffer -> set buffer layout and force rerender",
    "/health": "/health q[.<alias>] -> GET q profile health_url",
}


CONFIG_PREFIX = "#SYSTEM:config:"


def _force_render(parser) -> None:
    flags = parser.runtime.get("flags")
    if isinstance(flags, dict):
        flags["force_render"] = True


def _set_layout(parser, mode: str) -> None:
    out = parser.state.set("$SYSTEM.LAYOUT", mode)
    if out["error"]:
        raise RuntimeError(out["error"])


def _resolve_q_alias(token: str) -> str:
    if "." not in token:
        return "default"
    return token.split(".", 1)[1].strip() or "default"


def _state_set(parser, symbol: str, value) -> None:
    out = parser.state.set(symbol, value)
    if out["error"]:
        raise RuntimeError(out["error"])


def _delete_config_mirror(parser) -> None:
    out = parser.state.list_symbols()
    if out["error"]:
        raise RuntimeError(out["error"])

    for symbol in out["result"] or []:
        if isinstance(symbol, str) and symbol.startswith(CONFIG_PREFIX):
            deleted = parser.state.delete(symbol)
            if deleted["error"]:
                raise RuntimeError(deleted["error"])


def _mirror_config_leafs(parser, data, prefix=("SYSTEM", "config")) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            key = str(key)
            if key == "":
                raise ValueError("empty config key during mirror")
            _mirror_config_leafs(parser, value, prefix + (key,))
        return

    if isinstance(data, list):
        for idx, value in enumerate(data):
            _mirror_config_leafs(parser, value, prefix + (str(idx),))
        return

    target = "#" + ":".join(prefix)
    _state_set(parser, target, data)


def _reload_config(parser) -> None:
    config = load_config()

    _delete_config_mirror(parser)
    _mirror_config_leafs(parser, config)

    parser.runtime["config"] = config

    ctx = parser.runtime.get("ctx")
    if isinstance(ctx, dict):
        ctx["config"] = config

    active_profile = str(parser.runtime.get("q_profile") or "default").strip() or "default"
    try:
        set_active_profile(parser, active_profile)
    except Exception:
        set_active_profile(parser, "default")


def handler(line: str, parser) -> HandlerResponse:
    tokens = line.split()
    subcmd = tokens[0].lower()

    if subcmd == "/help":
        if len(tokens) == 1:
            items = []
            for name, short in parser.get_short_help().items():
                if name == "/":
                    items.append(short)
                else:
                    items.append(f"{name} -> {short}")
            return HandlerResponse(buffer_output="\n".join(items))
        target = tokens[1]
        if target.startswith("/"):
            text = SLASH_HELP.get(target, "")
            if text:
                return HandlerResponse(buffer_output=text)
        text = parser.get_full_help(target)
        if not text:
            return HandlerResponse(error=f"help not found: {target}")
        return HandlerResponse(buffer_output=text)

    if subcmd == "/time":
        return HandlerResponse(buffer_output=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if subcmd == "/exit":
        parser.should_exit = True
        return HandlerResponse(buffer_output="[ok] exit")

    if subcmd == "/greeting":
        return HandlerResponse(buffer_output=GREETING_TEXT)

    if subcmd == "/clear":
        out = parser.state.set("$SYSTEM.BUFFER", {})
        if out["error"]:
            return HandlerResponse(error=out["error"])
        _force_render(parser)
        return HandlerResponse()

    if subcmd == "/reload":
        try:
            _reload_config(parser)
        except Exception as exc:
            return HandlerResponse(error=str(exc))
        _force_render(parser)
        return HandlerResponse(buffer_output="[ok] config reloaded")

    if subcmd == "/buffer":
        try:
            _set_layout(parser, "buffer")
        except Exception as exc:
            return HandlerResponse(error=str(exc))
        _force_render(parser)
        return HandlerResponse()

    if subcmd == "/q" or subcmd.startswith("/q."):
        if len(tokens) != 1:
            return HandlerResponse(error="usage: /q[.<alias>]")
        alias = _resolve_q_alias(subcmd)
        try:
            set_active_profile(parser, alias)
            _set_layout(parser, "q")
        except Exception as exc:
            return HandlerResponse(error=str(exc))
        _force_render(parser)
        return HandlerResponse()

    if subcmd == "/health":
        if len(tokens) != 2:
            return HandlerResponse(error="usage: /health q[.<alias>]")
        target = tokens[1].lower()
        if not (target == "q" or target.startswith("q.")):
            return HandlerResponse(error="usage: /health q[.<alias>]")
        try:
            alias = _resolve_q_alias(target)
            return HandlerResponse(buffer_output=health_q_profile(parser, alias))
        except Exception as exc:
            return HandlerResponse(error=str(exc))

    return HandlerResponse(error=f"unknown slash command: {subcmd}")
