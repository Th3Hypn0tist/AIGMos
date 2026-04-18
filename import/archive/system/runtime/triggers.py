from __future__ import annotations

import json
import threading
import time
from queue import Queue
from typing import Any


class TriggerRuntime:
    def __init__(self, state, bus: Queue) -> None:
        self.state = state
        self.bus = bus
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}

    def add(self, name: str, left: str, right: str, persist: bool = True) -> None:
        with self._lock:
            self._items[name] = {
                "left": left,
                "right": right,
                "last": 0,
            }

        self.state.set(f"!{name}", 0)

        if persist:
            self._persist()

    def get_def(self, name: str) -> dict[str, str] | None:
        with self._lock:
            item = self._items.get(name)
            if item is None:
                return None

            return {
                "left": item["left"],
                "right": item["right"],
            }

    def remove(self, name: str, persist: bool = True) -> bool:
        with self._lock:
            existed = self._items.pop(name, None) is not None

        self.state.delete(f"!{name}")

        if existed and persist:
            self._persist()

        return existed

    def restore(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return

        for name, item in data.items():
            if not isinstance(item, dict):
                continue

            left = item.get("left")
            right = item.get("right")

            if not isinstance(left, str) or not isinstance(right, str):
                continue

            self.add(name, left, right, persist=False)

    def prime(self) -> None:
        with self._lock:
            items = list(self._items.items())

        for name, item in items:
            current = 1 if self._resolve(item["left"]) == self._resolve(item["right"]) else 0

            with self._lock:
                if name in self._items:
                    self._items[name]["last"] = current

            self.state.set(f"!{name}", current)

    def list_names(self) -> list[str]:
        with self._lock:
            return sorted(self._items.keys())

    def tick(self) -> None:
        with self._lock:
            items = list(self._items.items())

        for name, item in items:
            current = 1 if self._resolve(item["left"]) == self._resolve(item["right"]) else 0

            with self._lock:
                live = self._items.get(name)
                if live is None:
                    continue

                if current == live["last"]:
                    continue

                live["last"] = current

            self.state.set(f"!{name}", current)

            if current == 1:
                self.bus.put(name)

    def _persist(self) -> None:
        payload: dict[str, dict[str, str]] = {}

        with self._lock:
            for name, item in self._items.items():
                payload[name] = {
                    "left": item["left"],
                    "right": item["right"],
                }

        result = self.state.set("#SYSTEM:runtime:triggers", payload)
        if result["error"]:
            raise RuntimeError(result["error"])

    def _resolve(self, raw: str) -> Any:
        raw = raw.strip()

        if raw and raw[0] in "$#&%@!":
            return self.state.get(raw)["result"]

        try:
            return json.loads(raw)
        except Exception:
            return raw


class TriggerLoop(threading.Thread):
    def __init__(self, runtime: TriggerRuntime, poll_seconds: float = 0.05) -> None:
        super().__init__(daemon=True, name="triggers")
        self.runtime = runtime
        self.poll_seconds = float(poll_seconds)
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        print("[trigger-thread] started")
        while self._running:
            try:
                self.runtime.tick()
            except Exception as exc:
                print(f"[trigger-error] {type(exc).__name__}: {exc}")
            time.sleep(self.poll_seconds)
