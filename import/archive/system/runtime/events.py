from __future__ import annotations

import threading
from queue import Empty, Queue
from typing import Any


class EventRuntime:
    def __init__(self, state) -> None:
        self.state = state
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, list[str]]] = {}
        self._trigger_index: dict[str, list[str]] = {}

    def bind(self, trigger_name: str, event_name: str, command: str, persist: bool = True) -> None:
        with self._lock:
            item = self._items.setdefault(event_name, {"binds": [], "commands": []})

            if trigger_name not in item["binds"]:
                item["binds"].append(trigger_name)

            item["commands"].append(command)
            self._rebuild_index_locked()

        if persist:
            self._persist()

    def remove_event(self, event_name: str, persist: bool = True) -> bool:
        with self._lock:
            removed = self._items.pop(event_name, None) is not None
            if removed:
                self._rebuild_index_locked()

        if removed and persist:
            self._persist()

        return removed

    def restore(
        self,
        event_defs: dict[str, Any] | None = None,
        legacy_trigger_events: dict[str, Any] | None = None,
        legacy_event_commands: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self._items = {}

            if isinstance(event_defs, dict):
                self._restore_event_defs_locked(event_defs)
            else:
                self._restore_legacy_locked(legacy_trigger_events or {}, legacy_event_commands or {})

            self._rebuild_index_locked()

    def list_events(self) -> list[str]:
        with self._lock:
            return sorted(self._items.keys())

    def get_binds(self, event_name: str) -> list[str]:
        with self._lock:
            item = self._items.get(event_name)
            if item is None:
                return []
            return list(item["binds"])

    def get_commands(self, event_name: str) -> list[str]:
        with self._lock:
            item = self._items.get(event_name)
            if item is None:
                return []
            return list(item["commands"])

    def get_event_def(self, event_name: str) -> dict[str, list[str]] | None:
        with self._lock:
            item = self._items.get(event_name)
            if item is None:
                return None
            return {
                "binds": list(item["binds"]),
                "commands": list(item["commands"]),
            }

    def get_events_for_trigger(self, trigger_name: str) -> list[str]:
        with self._lock:
            return list(self._trigger_index.get(trigger_name, []))

    def emit_event(self, event_name: str, parser) -> None:
        for command in self.get_commands(event_name):
            parser.parse(command)

    def emit_trigger(self, trigger_name: str, parser) -> None:
        for event_name in self.get_events_for_trigger(trigger_name):
            self.emit_event(event_name, parser)

    def _restore_event_defs_locked(self, event_defs: dict[str, Any]) -> None:
        for event_name, item in event_defs.items():
            if not isinstance(event_name, str) or not event_name:
                continue

            if not isinstance(item, dict):
                continue

            binds = item.get("binds")
            commands = item.get("commands")

            if not isinstance(binds, list) or not isinstance(commands, list):
                continue

            clean_binds = [x for x in binds if isinstance(x, str) and x]
            clean_commands = [x for x in commands if isinstance(x, str) and x]

            if not clean_binds and not clean_commands:
                continue

            self._items[event_name] = {
                "binds": clean_binds,
                "commands": clean_commands,
            }

    def _restore_legacy_locked(
        self,
        trigger_events: dict[str, Any],
        event_commands: dict[str, Any],
    ) -> None:
        for event_name, commands in event_commands.items():
            if not isinstance(event_name, str) or not event_name:
                continue
            if not isinstance(commands, list):
                continue

            clean_commands = [x for x in commands if isinstance(x, str) and x]
            if clean_commands:
                self._items[event_name] = {
                    "binds": [],
                    "commands": clean_commands,
                }

        for trigger_name, events in trigger_events.items():
            if not isinstance(trigger_name, str) or not trigger_name:
                continue
            if not isinstance(events, list):
                continue

            for event_name in events:
                if not isinstance(event_name, str) or not event_name:
                    continue

                item = self._items.setdefault(event_name, {"binds": [], "commands": []})
                if trigger_name not in item["binds"]:
                    item["binds"].append(trigger_name)

    def _rebuild_index_locked(self) -> None:
        self._trigger_index = {}

        for event_name, item in self._items.items():
            for trigger_name in item["binds"]:
                self._trigger_index.setdefault(trigger_name, []).append(event_name)

        for trigger_name in self._trigger_index:
            self._trigger_index[trigger_name].sort()

    def _persist(self) -> None:
        with self._lock:
            payload = {
                event_name: {
                    "binds": list(item["binds"]),
                    "commands": list(item["commands"]),
                }
                for event_name, item in self._items.items()
            }

        result = self.state.set("#SYSTEM:runtime:events", payload)
        if result["error"]:
            raise RuntimeError(result["error"])

        self.state.delete("#SYSTEM:runtime:trigger_events")
        self.state.delete("#SYSTEM:runtime:event_commands")


class EventLoop(threading.Thread):
    def __init__(self, bus: Queue, runtime: EventRuntime, parser) -> None:
        super().__init__(daemon=True, name="events")
        self.bus = bus
        self.runtime = runtime
        self.parser = parser
        self._running = True

    def stop(self) -> None:
        self._running = False

# system/runtime/events.py
    def run(self) -> None:
        print("[event-thread] started")
        while self._running:
            try:
                name = self.bus.get(timeout=0.1)
            except Empty:
                continue

            try:
                self.runtime.emit_trigger(name, self.parser)
            except Exception as exc:
                print(f"[event-error] {type(exc).__name__}: {exc}")
