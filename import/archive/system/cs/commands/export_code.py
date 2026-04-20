# system/cs/commands/export_code.py

from __future__ import annotations

import shlex

from system.cs.lib.file_export import export_code
from system.cs.parser import HandlerResponse


command = "export.code"
help_short = "export.code <src> <dst>"
help_full = (
    "export.code <src> <dst>\n"
    "\n"
    "Examples:\n"
    "  export.code #code ./out\n"
    "  export.code $MEM:build ./out\n"
    "  export.code #code:main.py ./main.py\n"
    "  export.code $MEM:build $MEM:path\n"
    "\n"
    "Semantics:\n"
    "- src first\n"
    "- dst second\n"
    "- src may be:\n"
    "  1) one raw string leaf -> write one file\n"
    "  2) one JSON object string leaf -> export manifest\n"
    "  3) one object leaf -> export manifest\n"
    "  4) one # subtree of string leaves -> export recursive tree\n"
    "- manifest supports:\n"
    "  - flat path -> string\n"
    "  - nested object tree\n"
    "- arrays, numbers, bools and null are invalid in manifest mode\n"
    "- dst may be literal filesystem path or symbol containing path\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"export.code parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: export.code <src> <dst>")

    _, src, dst = parts

    try:
        export_code(parser, src, dst)
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
