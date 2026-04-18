# system/adapters/mem.py
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any


class MemAdapter:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self._lock = RLock()

    def get(self, symbol: str) -> Any:
        with self._lock:
            value = self.store.get(symbol)
        return deepcopy(value)

    def set(self, symbol: str, value: Any) -> None:
        with self._lock:
            self.store[symbol] = deepcopy(value)

    def delete(self, symbol: str) -> None:
        with self._lock:
            self.store.pop(symbol, None)

    def list_symbols(self) -> list[str]:
        with self._lock:
            return sorted(self.store.keys())
