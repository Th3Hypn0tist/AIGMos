# system/bootstrap.py

from __future__ import annotations

import threading
from queue import Queue
from typing import Any

from system.adapters.registry import build_state_request, create_adapter
from system.inputs.registry import create_input, list_input_names
from system.boot import bind_boot_flags, run_boot_hooks
from system.config import STATE_DB_PATH, load_config, require_osc_in_config
from system.cs.parser import Parser
from system.layout.render import push_live_line
from system.lib.library_reload import run_init_cs
from system.runtime.events import EventLoop, EventRuntime
from system.runtime.osc import OSCInServer
from system.runtime.runner import (
    STATUS_RUN,
    STATUS_WAIT,
    create_runner,
    ensure_worker,
    set_runner_status,
)
from system.runtime.runner_store import load_runner_defs
from system.runtime.triggers import TriggerLoop, TriggerRuntime
from system.state.api import read_value, write_value
from system.state.engine import StateEngine


def _state_get_value(state, symbol: str) -> Any:
    return read_value(state, symbol, None)


def _state_set(state, symbol: str, value: Any) -> None:
    out = write_value(state, symbol, value, writer="bootstrap", op="bootstrap_set")
    if out["error"]:
        raise ValueError(f"state.write_state failed for {symbol}: {out['error']}")


def _ensure_default(state, symbol: str, value: Any) -> None:
    current = _state_get_value(state, symbol)
    if current is None:
        _state_set(state, symbol, value)


def _default_layout_handle(config: dict) -> str:
    raw = str(config.get("layout", "cs") or "cs").strip()
    token = raw[1:] if raw.startswith("/") else raw
    lower = token.lower()
    if lower in {"cs", "buffer"}:
        return "|CS"
    if lower == "q":
        return "|Q"
    if lower == "monitor":
        return "|MONITOR"
    return "|CS"


def _ensure_system_defaults(state, config: dict) -> None:
    _default_layout_handle(config)
    _ensure_default(state, "$SYSTEM.ERRORS", {})


def _should_run_init_cs(state) -> bool:
    done = _state_get_value(state, "#SYSTEM:boot:init_cs_done")
    if str(done or '').strip() in {'1', 'true', 'True', 'yes', 'on'}:
        return False
    # migration path for older states that already contain the imported libraries
    if all(_state_get_value(state, symbol) is not None for symbol in ("#HELP", "#ROLES", "#P", "#R")):
        _state_set(state, "#SYSTEM:boot:init_cs_done", 1)
        return False
    return True


def _mirror_config_leafs(state, data, prefix=("SYSTEM", "config")) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            key = str(key)
            if key == "":
                raise ValueError("empty config key during mirror")
            _mirror_config_leafs(state, value, prefix + (key,))
        return

    if isinstance(data, list):
        for idx, value in enumerate(data):
            _mirror_config_leafs(state, value, prefix + (str(idx),))
        return

    target = "#" + ":".join(prefix)
    _state_set(state, target, data)


def _build_state(config: dict) -> tuple[StateEngine, Any, Any, Any, list[tuple[str, Any]]]:
    sqlite_adapter = create_adapter("sqlite", path=STATE_DB_PATH)
    raw_state, mem_adapter, extra_routes = build_state_request(sqlite_adapter, config)
    osc_input = create_input("osc", backend=mem_adapter, root_symbol="#OSC")

    state = StateEngine(raw_state)
    return state, sqlite_adapter, mem_adapter, osc_input, extra_routes


def _restore_runtime_state(state, triggers: TriggerRuntime, events: EventRuntime) -> None:
    trigger_defs = _state_get_value(state, "#SYSTEM:runtime:triggers")
    event_defs = _state_get_value(state, "#SYSTEM:runtime:events")
    if isinstance(trigger_defs, dict):
        triggers.restore(trigger_defs)

    if isinstance(event_defs, dict):
        events.restore(event_defs)

    triggers.prime()


def _dispatch_runner_raw(parser, raw: str, cancel_event=None):
    err = parser.parse(raw)
    if err:
        raise RuntimeError(err)
    return None


def _restore_runners_and_apply_autostart(state, parser) -> None:
    defs = load_runner_defs(state)

    for name, item in defs.items():
        create_runner(
            source=item["source"],
            lines=item["lines"],
            mode=item["mode"],
            name=name,
            status=STATUS_WAIT,
            autostart=item.get("autostart", 0),
        )

    autostart_names = [
        name
        for name, item in defs.items()
        if int(item.get("autostart", 0) or 0) > 0
    ]
    autostart_names.sort(key=lambda name: int(defs[name].get("autostart", 0) or 0))

    for name in autostart_names:
        set_runner_status(name, STATUS_RUN)

    ensure_worker(
        lambda raw, cancel_event=None: _dispatch_runner_raw(
            parser, raw, cancel_event=cancel_event
        )
    )


def build_ctx() -> dict[str, Any]:
    config = load_config()

    state, sqlite_adapter, mem_adapter, osc_input, extra_routes = _build_state(config)

    _ensure_system_defaults(state, config)
    _mirror_config_leafs(state, config)

    parser = Parser(state)
    parser.execute = parser.parse
    parser.dispatch = parser.parse
    parser.run_line = parser.parse

    trigger_bus: Queue = Queue()
    triggers = TriggerRuntime(state, trigger_bus)
    events = EventRuntime(state)

    flags = {
        "running": True,
        "force_render": False,
    }

    ctx = {
        "config": config,
        "state": state,
        "parser": parser,
        "flags": flags,
        "layout": _default_layout_handle(config),
        "sqlite_adapter": sqlite_adapter,
        "mem_adapter": mem_adapter,
        "osc_input": osc_input,
        "input_types": list_input_names(),
        "state_routes": list(extra_routes),
        "trigger_bus": trigger_bus,
        "triggers": triggers,
        "events": events,
    }

    parser.runtime["config"] = config
    parser.runtime["ctx"] = ctx
    parser.runtime["flags"] = flags
    parser.runtime["ui_thread_id"] = threading.get_ident()
    parser.runtime["buffer_live_push"] = lambda text: push_live_line(ctx, text)
    parser.runtime["trigger_bus"] = trigger_bus
    parser.runtime["triggers"] = triggers
    parser.runtime["events"] = events
    parser.runtime["osc_input"] = osc_input
    parser.runtime["q_profile"] = "default"
    parser.runtime["q_chat_symbol"] = ""
    parser.runtime["q_response_symbol"] = ""
    parser.runtime["q_thinking_symbol"] = ""
    setattr(state, "_aigmos_runtime", parser.runtime)

    bind_boot_flags(flags)
    run_boot_hooks(state, flags)

    def _boot_startup() -> None:
        try:
            if _should_run_init_cs(state):
                run_init_cs(parser)
                _state_set(state, "#SYSTEM:boot:init_cs_done", 1)

            _restore_runtime_state(state, triggers, events)
            _restore_runners_and_apply_autostart(state, parser)

            trigger_loop = TriggerLoop(triggers)
            event_loop = EventLoop(trigger_bus, events, parser)

            bind_ip, port, buffer_size = require_osc_in_config(state)
            osc_server = OSCInServer(bind_ip, port, buffer_size, osc_input)

            ctx["osc_server"] = osc_server
            ctx["trigger_loop"] = trigger_loop
            ctx["event_loop"] = event_loop

            event_loop.start()
            trigger_loop.start()
            osc_server.start()
        except Exception as exc:
            try:
                from system.boot import boot_log
                boot_log(f"[boot-error] {type(exc).__name__}: {exc}")
            except Exception:
                pass
            flags['boot_startup_error'] = f"{type(exc).__name__}: {exc}"
        finally:
            flags['boot_startup_done'] = True
            flags['boot_wait_for_key'] = True
            flags['force_render'] = True

    ctx["boot_startup"] = _boot_startup

    return ctx
