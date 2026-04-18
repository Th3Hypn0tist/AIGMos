# system/cs/commands/import_file.py

from __future__ import annotations

import shlex

from system.cs.lib.file_import import (
    read_text_file,
    resolve_source_path,
    validate_data_symbol,
)
from system.cs.lib.ops import list_symbols
from system.cs.parser import HandlerResponse


command = "import.file"
help_short = "import.file <src> <target>"
help_full = (
    "import.file <src> <target>\n"
    "\n"
    "Examples:\n"
    "  import.file ./README.md $MEM:readme\n"
    "  import.file ./notes.txt #docs:raw:file\n"
    "  import.file $MEM:path $MEM:file\n"
    "\n"
    "Semantics:\n"
    "- src first\n"
    "- target second\n"
    "- src may be literal filesystem path or symbol containing path\n"
    "- src must be one UTF-8 text file\n"
    "- target must be one $, # or & symbol\n"
    "- whole file content is stored as one symbol value\n"
    "- existing target value and child symbols are cleared first\n"
)


def _clear_target_if_exists(parser, target: str) -> None:
    matches = [
        symbol
        for symbol in list_symbols(parser.state)
        if symbol == target
        or symbol.startswith(target + ":")
        or symbol.startswith(target + ".")
    ]

    for symbol in sorted(matches, key=len, reverse=True):
        out = parser.state.delete(symbol)
        if out["error"]:
            raise ValueError(out["error"])


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"import.file parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: import.file <src> <target>")

    _, src_token, target = parts

    try:
        validate_data_symbol(target)
        src_path = resolve_source_path(parser, src_token)
        text = read_text_file(src_path)

        _clear_target_if_exists(parser, target)

        out = parser.state.set(target, text)
        if out["error"]:
            return HandlerResponse(error=out["error"])

    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
