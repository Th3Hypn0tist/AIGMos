# system/cs/commands/import_json.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import json

from system.cs.lib.ops import list_symbols
from system.cs.command_args import parse_argv
from system.cs.state_ops import delete_result, get_optional, set_result
from system.cs.symbol_rules import require_symbol

command = "import.json"
help_short = 'import.json <input> <output>'
help_full = """import JSON text into state structure

current implementation:
- input first
- output last
- input may be a symbol containing JSON text
- output target determines whether result lands in $, &, or #
- import resets and overwrites target content

note:
- this help describes the current command implementation
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, src, dst = parse_argv(line, usage="usage: import.json <input:symbol> #output", label="import.json", exact=2)
        require_symbol(src, allowed="$#&", role="input")
        require_symbol(dst, allowed="#", role="output")
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        _ensure_no_children(parser.state, src)

        raw = get_optional(parser.state, src)
        if raw is None:
            return HandlerResponse(error=str('input not found' or ""))

        if not isinstance(raw, str):
            return HandlerResponse(error=str('input must contain a direct string value' or ""))

        try:
            value = json.loads(raw)
        except Exception as exc:
            return HandlerResponse(error=str(f'invalid json: {exc}' or ""))

        _clear_output_root(parser.state, dst)
        _write_json_to_hash(parser.state, dst, value)
        return HandlerResponse(buffer_output=str(dst or ""))

    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))


def _ensure_no_children(state, src: str) -> None:
    prefix = src + ":"
    for symbol in list_symbols(state):
        if symbol.startswith(prefix):
            raise ValueError("input must not have child symbols")


def _clear_output_root(state, dst: str) -> None:
    prefix = dst + ":"
    for symbol in list_symbols(state):
        if symbol == dst or symbol.startswith(prefix):
            delete_result(state, symbol, writer="parser:import.json", op="import_json_clear_output")


def _write_json_to_hash(state, target: str, value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _write_json_to_hash(state, f"{target}:{key}", child)
        return

    if isinstance(value, list):
        for idx, child in enumerate(value):
            _write_json_to_hash(state, f"{target}:{idx}", child)
        return

    set_result(state, target, value, writer="parser:import.json", op="import_json_write_leaf")

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

