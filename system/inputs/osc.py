from __future__ import annotations

from typing import Any


class OSCInput:
    def __init__(self, backend, root_symbol: str = "#OSC") -> None:
        self.backend = backend
        self.root_symbol = str(root_symbol or "#OSC").strip() or "#OSC"

    def apply_packet(self, address: str, args: list[Any]) -> str:
        symbol = self.address_to_symbol(address, root_symbol=self.root_symbol)
        value = self.args_to_value(args)
        self.backend.set(symbol, value)
        return symbol

    @staticmethod
    def address_to_symbol(address: str, *, root_symbol: str = "#OSC") -> str:
        parts = [part for part in str(address or "").strip("/").split("/") if part]
        if not parts:
            raise ValueError("invalid OSC address")
        return str(root_symbol).rstrip(":") + ":" + ":".join(parts)

    @staticmethod
    def args_to_value(args: list[Any]) -> Any:
        if not args:
            return 1
        if len(args) == 1:
            return args[0]
        return list(args)



def create_input(**kwargs):
    return OSCInput(**kwargs)
