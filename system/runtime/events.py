from __future__ import annotations

import threading
from queue import Empty, Queue
from typing import Any

from system.boot import boot_log
from system.lib.trigger.event_runtime import dispatch_event, dispatch_events_for_trigger
from system.lib.trigger.lifecycle import create_event, remove_event
from system.lib.trigger.store import list_event_names, list_events_for_trigger, load_event_def
from system.lib.trigger.types import EventDef


class EventRuntime:
    def __init__(self, state) -> None:
        self.state = state
        self._lock = threading.RLock()

    def bind(self, trigger_name: str, event_name: str, command: str, persist: bool = True) -> None:
        _ = persist
        create_event(self.state, EventDef(name=event_name, trigger_name=trigger_name, command=command))

    def remove_event(self, event_name: str, persist: bool = True) -> bool:
        _ = persist
        return bool(remove_event(self.state, event_name))

    def restore(
        self,
        event_defs: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(event_defs, dict):
            return
        for event_name, item in event_defs.items():
            if not isinstance(event_name, str) or not isinstance(item, dict):
                continue
            if load_event_def(self.state, event_name) is not None:
                continue
            trigger_name = str(item.get('trigger') or '').strip()
            command = str(item.get('command') or '').strip()
            if trigger_name and command:
                create_event(self.state, EventDef(name=event_name, trigger_name=trigger_name, command=command))

    def list_events(self) -> list[str]:
        with self._lock:
            return list_event_names(self.state)

    def get_binds(self, event_name: str) -> list[str]:
        with self._lock:
            event_def = load_event_def(self.state, event_name)
            return [event_def.trigger_name] if event_def is not None else []

    def get_commands(self, event_name: str) -> list[str]:
        with self._lock:
            event_def = load_event_def(self.state, event_name)
            return [event_def.command] if event_def is not None else []

    def get_event_def(self, event_name: str) -> dict[str, list[str]] | None:
        with self._lock:
            event_def = load_event_def(self.state, event_name)
            if event_def is None:
                return None
            return {
                'binds': [event_def.trigger_name],
                'commands': [event_def.command],
            }

    def get_events_for_trigger(self, trigger_name: str) -> list[str]:
        with self._lock:
            return [item.name for item in list_events_for_trigger(self.state, trigger_name)]

    def emit_event(self, event_name: str, parser) -> None:
        event_def = load_event_def(self.state, event_name)
        if event_def is None:
            return
        dispatch_event(self.state, event_def, parser=parser)

    def emit_trigger(self, trigger_name: str, parser) -> None:
        dispatch_events_for_trigger(self.state, trigger_name, parser=parser)




class EventLoop(threading.Thread):
    def __init__(self, bus: Queue, runtime: EventRuntime, parser) -> None:
        super().__init__(daemon=True, name="events")
        self.bus = bus
        self.runtime = runtime
        self.parser = parser
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        boot_log("[event-thread] started")
        while self._running:
            try:
                name = self.bus.get(timeout=0.1)
            except Empty:
                continue
            try:
                self.runtime.emit_trigger(name, self.parser)
            except Exception as exc:
                boot_log(f"[event-error] {type(exc).__name__}: {exc}")
