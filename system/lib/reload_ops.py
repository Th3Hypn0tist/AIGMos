from __future__ import annotations

from system.adapters.registry import build_extra_routes, reload_adapters
from system.config import load_config, require_osc_in_config
from system.cs.command_registry import reload_commands
from system.cs.runtime_ctx import get_ctx, get_runtime, set_runtime
from system.cs.state_ops import delete_result, set_result
from system.inputs.registry import create_input, list_input_names, reload_inputs
from system.lib.q.profile import set_active_profile
from system.runtime.osc import OSCInServer

CONFIG_PREFIX = "#SYSTEM:config:"
_RELOADABLE = ("config", "commands", "layout", "adapters", "inputs")


def _state_set(parser, symbol: str, value, *, op: str = "reload_set") -> None:
    set_result(parser.state, symbol, value, writer="parser:reload", op=op)


def _state_delete(parser, symbol: str, *, op: str = "reload_delete") -> None:
    delete_result(parser.state, symbol, writer="parser:reload", op=op)


def _list_all_symbols(parser) -> list[str]:
    out = parser.state.list_symbols()
    if out["error"]:
        raise RuntimeError(out["error"])
    return [symbol for symbol in (out["result"] or []) if isinstance(symbol, str)]


def _delete_config_mirror(parser) -> None:
    for symbol in _list_all_symbols(parser):
        if symbol.startswith(CONFIG_PREFIX):
            _state_delete(parser, symbol, op="reload_delete_config_mirror")


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
    _state_set(parser, target, data, op="reload_mirror_config")


def reload_config(parser) -> dict:
    config = load_config()
    _delete_config_mirror(parser)
    _mirror_config_leafs(parser, config)
    set_runtime(parser, "config", config)
    ctx = get_ctx(parser)
    if isinstance(ctx, dict):
        ctx["config"] = config

    active_profile = str(get_runtime(parser, "q_profile", "default") or "default").strip() or "default"
    try:
        set_active_profile(parser, active_profile)
    except Exception:
        set_active_profile(parser, "default")
    return config


def reload_commands_only(parser) -> list[str]:
    parser.registry = reload_commands()
    return sorted(parser.registry.keys())


def reload_layout_only(parser) -> list[str]:
    from system.layout import registry as layout_registry

    ctx = get_ctx(parser)
    return layout_registry.reload_layout(ctx)


def reload_adapters_only(parser) -> list[str]:
    ctx = get_ctx(parser)
    config = ctx.get("config") if isinstance(ctx, dict) else None

    names = reload_adapters()

    state = ctx.get("state") if isinstance(ctx, dict) else None
    old_routes = list(ctx.get("state_routes") or []) if isinstance(ctx, dict) else []
    for prefix, _adapter in old_routes:
        try:
            state.unregister_route(prefix)
        except Exception:
            pass

    extra_routes = build_extra_routes(config)
    if state is not None:
        for prefix, adapter in extra_routes:
            state.register_route(prefix, adapter)

    if isinstance(ctx, dict):
        ctx["state_routes"] = list(extra_routes)
    return names


def _restart_osc_input(parser) -> None:
    ctx = get_ctx(parser)
    if not isinstance(ctx, dict):
        return

    old_server = ctx.get("osc_server")
    if old_server is not None and hasattr(old_server, "stop"):
        try:
            old_server.stop()
        except Exception:
            pass
        try:
            old_server.join(timeout=1.0)
        except Exception:
            pass

    osc_input = create_input("osc", backend=ctx.get("mem_adapter"), root_symbol="#OSC")
    bind_ip, port, buffer_size = require_osc_in_config(ctx["state"])
    osc_server = OSCInServer(bind_ip, port, buffer_size, osc_input)
    osc_server.start()

    ctx["osc_input"] = osc_input
    ctx["osc_server"] = osc_server
    ctx["input_types"] = list_input_names()
    parser.runtime["osc_input"] = osc_input


def reload_inputs_only(parser) -> list[str]:
    names = reload_inputs()
    _restart_osc_input(parser)
    ctx = get_ctx(parser)
    if isinstance(ctx, dict):
        ctx["input_types"] = names
    return names


def parse_reload_targets(tokens: list[str]) -> list[str]:
    if len(tokens) <= 1:
        return ["config"]

    raw = " ".join(tokens[1:]).strip()
    if not raw:
        return ["config"]

    normalized = raw.replace(",", "/").replace(" ", "/")
    parts = [part.strip().lower() for part in normalized.split("/") if part.strip()]
    if not parts:
        return ["config"]

    if "all" in parts:
        return list(_RELOADABLE)

    seen: list[str] = []
    for part in parts:
        if part not in _RELOADABLE:
            raise ValueError(f"unknown reload target: {part}")
        if part not in seen:
            seen.append(part)
    return seen


def reload_selected(parser, targets: list[str]) -> list[str]:
    completed: list[str] = []
    for target in targets:
        if target == "config":
            reload_config(parser)
        elif target == "commands":
            reload_commands_only(parser)
        elif target == "layout":
            reload_layout_only(parser)
        elif target == "adapters":
            reload_adapters_only(parser)
        elif target == "inputs":
            reload_inputs_only(parser)
        else:
            raise ValueError(f"unknown reload target: {target}")
        completed.append(target)
    return completed


__all__ = [
    "reload_config",
    "reload_commands_only",
    "reload_layout_only",
    "reload_adapters_only",
    "reload_inputs_only",
    "parse_reload_targets",
    "reload_selected",
]
