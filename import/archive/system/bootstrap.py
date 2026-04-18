# system/bootstrap.py

from __future__ import annotations

import threading
from queue import Queue
from typing import Any

from system.adapters.osc import OSCAdapter
from system.adapters.sqlite import SQLiteAdapter
from system.boot import run_boot_hooks
from system.config import STATE_DB_PATH, load_config, require_osc_in_config
from system.cs.parser import Parser
from system.layout.render import push_live_line
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
from system.state.request import StateRequest


def _state_get_value(state, symbol: str) -> Any:
    out = state.get(symbol)
    if out["error"]:
        return None
    return out["result"]


def _state_set(state, symbol: str, value: Any) -> None:
    out = state.set(symbol, value)
    if out["error"]:
        raise ValueError(f"state.set failed for {symbol}: {out['error']}")


def _ensure_default(state, symbol: str, value: Any) -> None:
    current = _state_get_value(state, symbol)
    if current is None:
        _state_set(state, symbol, value)


def _ensure_system_defaults(state, config: dict) -> None:
    _ensure_default(state, "$SYSTEM.BUFFER", {})
    _ensure_default(state, "$SYSTEM.ERRORS", {})
    _ensure_default(state, "$SYSTEM.LAYOUT", config.get("layout", "buffer"))
    _ensure_default(state, "$CH:q", {"turns": []})
    _ensure_default(state, "#SYSTEM:keymap:alt:0", "/buffer")


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


def _build_state() -> tuple[StateRequest, SQLiteAdapter, OSCAdapter]:
    sqlite_adapter = SQLiteAdapter(STATE_DB_PATH)
    osc_adapter = OSCAdapter()

    state = StateRequest(sqlite_adapter)
    state.register_route("#OSC", osc_adapter)

    return state, sqlite_adapter, osc_adapter


def _restore_runtime_state(state, triggers: TriggerRuntime, events: EventRuntime) -> None:
    trigger_defs = _state_get_value(state, "#SYSTEM:runtime:triggers")
    event_defs = _state_get_value(state, "#SYSTEM:runtime:events")
    legacy_trigger_events = _state_get_value(state, "#SYSTEM:runtime:trigger_events")
    legacy_event_commands = _state_get_value(state, "#SYSTEM:runtime:event_commands")

    if isinstance(trigger_defs, dict):
        triggers.restore(trigger_defs)

    if isinstance(event_defs, dict):
        events.restore(event_defs)
    elif isinstance(legacy_trigger_events, dict) or isinstance(legacy_event_commands, dict):
        events.restore(None, legacy_trigger_events or {}, legacy_event_commands or {})

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

    state, sqlite_adapter, osc_adapter = _build_state()

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
        "layout": config.get("layout", "buffer"),
        "sqlite_adapter": sqlite_adapter,
        "osc_adapter": osc_adapter,
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
    parser.runtime["osc_adapter"] = osc_adapter
    parser.runtime["q_profile"] = "default"
    parser.runtime["q_chat_symbol"] = "$CH:q"

    run_boot_hooks(state, flags)

    _restore_runtime_state(state, triggers, events)
    _restore_runners_and_apply_autostart(state, parser)

    trigger_loop = TriggerLoop(triggers)
    event_loop = EventLoop(trigger_bus, events, parser)

    bind_ip, port, buffer_size = require_osc_in_config(state)
    osc_server = OSCInServer(bind_ip, port, buffer_size, osc_adapter)

    ctx["osc_server"] = osc_server
    ctx["trigger_loop"] = trigger_loop
    ctx["event_loop"] = event_loop

    event_loop.start()
    trigger_loop.start()
    osc_server.start()
    print ("""
    Startup done!
    
    """)

    return ctx
