# system/cs/commands/import_file.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv

from system.cs.lib.file_import import (
    read_text_file,
    resolve_source_path,
    validate_data_symbol,
)
from system.cs.lib.ops import list_symbols
from system.cs.state_ops import delete_result, set_result


command = "import.file"
help_short = 'import.file <src> <target>'
help_full = """import one filesystem file into one symbol target

current implementation:
- src first
- target last
- src may be literal path or symbol containing a path
- target receives file text as one value

note:
- this help describes the current command implementation
"""

def _clear_target_if_exists(parser, target: str) -> None:
    matches = [
        symbol
        for symbol in list_symbols(parser.state)
        if symbol == target
        or symbol.startswith(target + ":")
        or symbol.startswith(target + ".")
    ]

    for symbol in sorted(matches, key=len, reverse=True):
        delete_result(parser.state, symbol, writer="parser:import.file", op="import_file_clear_target")


def handler(line: str, parser) -> HandlerResponse:
    try:
        _, src_token, target = parse_argv(
            line,
            usage="usage: import.file <src> <target>",
            label="import.file",
            exact=2,
        )
        validate_data_symbol(target)
        src_path = resolve_source_path(parser, src_token)
        text = read_text_file(src_path)

        _clear_target_if_exists(parser, target)

        set_result(parser.state, target, text, writer="parser:import.file", op="import_file_set_target")

    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str('[ok]' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

