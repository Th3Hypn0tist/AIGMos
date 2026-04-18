from __future__ import annotations

from system.state.api import list_symbols

from .lib import io as layout_io

_state_delete = layout_io.state_delete


def delete_layout_symbols(state, prefixes: list[str], *, writer: str = 'layout:store') -> None:
    if not prefixes:
        return
    targets = [str(prefix or '').strip() for prefix in prefixes if str(prefix or '').strip()]
    if not targets:
        return
    symbols = list_symbols(state)
    doomed: set[str] = set()
    for symbol in symbols:
        for prefix in targets:
            if symbol == prefix or symbol.startswith(prefix + ':'):
                doomed.add(symbol)
                break
    for symbol in sorted(doomed, reverse=True):
        _state_delete(state, symbol, writer=writer, op='layout_delete')
