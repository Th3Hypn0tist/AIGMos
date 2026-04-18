# system/adapters/mem.py
from __future__ import annotations

from copy import deepcopy
from typing import Any


class MemAdapter:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def get(self, symbol: str) -> Any:
        value = self.store.get(symbol)
        return deepcopy(value)

    def set(self, symbol: str, value: Any) -> None:
        self.store[symbol] = deepcopy(value)

    def delete(self, symbol: str) -> None:
        self.store.pop(symbol, None)

    def list_symbols(self) -> list[str]:
        return sorted(self.store.keys())
