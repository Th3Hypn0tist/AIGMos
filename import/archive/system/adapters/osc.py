# system/adapters/osc.py
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any


class OSCAdapter:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self._lock = RLock()

    def get(self, symbol: str) -> Any:
        base, index = self._split_selector(symbol)
        with self._lock:
            value = deepcopy(self.store.get(base))
        if index is None:
            return value
        if not isinstance(value, list):
            return None
        if index < 0 or index >= len(value):
            return None
        return deepcopy(value[index])

    def set(self, symbol: str, value: Any) -> None:
        with self._lock:
            self.store[symbol] = deepcopy(value)

    def delete(self, symbol: str) -> None:
        base, index = self._split_selector(symbol)
        with self._lock:
            if index is None:
                self.store.pop(base, None)
                return

            value = self.store.get(base)
            if not isinstance(value, list):
                return
            if index < 0 or index >= len(value):
                return

            next_value = list(value)
            del next_value[index]
            if not next_value:
                self.store.pop(base, None)
            elif len(next_value) == 1:
                self.store[base] = deepcopy(next_value[0])
            else:
                self.store[base] = deepcopy(next_value)

    def list_symbols(self) -> list[str]:
        with self._lock:
            return sorted(self.store.keys())

    def snapshot(self, prefix: str | None = None) -> dict[str, Any]:
        with self._lock:
            if prefix is None:
                return deepcopy(self.store)
            return {
                key: deepcopy(value)
                for key, value in self.store.items()
                if key.startswith(prefix)
            }

    def apply_packet(self, address: str, args: list[Any]) -> str:
        symbol = self.address_to_symbol(address)
        value = self.args_to_value(args)
        self.set(symbol, value)
        return symbol

    @staticmethod
    def address_to_symbol(address: str) -> str:
        parts = [part for part in address.strip("/").split("/") if part]
        if not parts:
            raise ValueError("invalid OSC address")
        return "#OSC:" + ":".join(parts)

    @staticmethod
    def args_to_value(args: list[Any]) -> Any:
        if not args:
            return 1
        if len(args) == 1:
            return args[0]
        return list(args)

    @staticmethod
    def _split_selector(symbol: str) -> tuple[str, int | None]:
        if "/" not in symbol:
            return symbol, None
        base, tail = symbol.rsplit("/", 1)
        if not tail.isdigit():
            return symbol, None
        return base, int(tail)
