from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.lib.map.files import build_file_rows
from system.lib.symbols import validate_symbol, write_symbol_value

command = "map.files"
help_short = "map.files #input [$output]"
help_full = (
    "create a structure-only file path map from a # subtree\n\n"
    "usage:\n"
    "  map.files #input\n"
    "  map.files #input $output\n\n"
    "rules:\n"
    "- input must be a # symbol\n"
    "- optional output must be a $ symbol\n"
    "- with one argument, result is written directly to buffer\n"
    "- with two arguments, result is written into $output\n"
    "- directories end with /\n"
    "- files do not end with /\n"
    "- names are preserved exactly\n"
    "- file contents are not copied"
)


def handler(line: str, parser):
    parts = line.split()
    if len(parts) not in (2, 3):
        return HandlerResponse(error=str('usage: map.files #input [$output]' or ""))

    if len(parts) == 2:
        _, src = parts
        dst = None
    else:
        _, src, dst = parts

    try:
        validate_symbol(src, allowed="#", role="input")
        if dst is not None:
            validate_symbol(dst, allowed="$", role="output")
        rows = build_file_rows(parser.state, src)
        result = "\n".join(rows)
        if dst is None:
            return HandlerResponse(buffer_output=str(result or ""))
        write_symbol_value(parser.state, dst, result, writer="parser:map.files", op="map_files_symbol")
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

