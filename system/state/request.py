# system/state/request.py
from __future__ import annotations

from typing import Any


class StateRequest:
    def __init__(self, default_adapter) -> None:
        self.default_adapter = default_adapter
        self.routes: dict[str, Any] = {}

    def register_route(self, prefix: str, adapter) -> None:
        self.routes[prefix] = adapter

    def unregister_route(self, prefix: str) -> None:
        self.routes.pop(prefix, None)


    def _resolve(self, symbol: str):
        if not symbol or symbol[0] not in "$#&%@!|":
            raise ValueError(f"invalid symbol: {symbol}")

        for prefix in sorted(self.routes.keys(), key=len, reverse=True):
            if symbol.startswith(prefix):
                return self.routes[prefix]

        return self.default_adapter

    def get(self, symbol: str) -> dict[str, Any]:
        try:
            return {"result": self._resolve(symbol).get(symbol), "error": ""}
        except Exception as e:
            return {"result": None, "error": str(e)}

    def set(self, symbol: str, value: Any) -> dict[str, Any]:
        try:
            self._resolve(symbol).set(symbol, value)
            return {"result": value, "error": ""}
        except Exception as e:
            return {"result": None, "error": str(e)}

    def delete(self, symbol: str) -> dict[str, Any]:
        try:
            self._resolve(symbol).delete(symbol)
            return {"result": None, "error": ""}
        except Exception as e:
            return {"result": None, "error": str(e)}

    def list_symbols(self) -> dict[str, Any]:
        try:
            symbols = set(self.default_adapter.list_symbols())
            for adapter in self.routes.values():
                symbols.update(adapter.list_symbols())
            return {"result": sorted(symbols), "error": ""}
        except Exception as e:
            return {"result": None, "error": str(e)}
