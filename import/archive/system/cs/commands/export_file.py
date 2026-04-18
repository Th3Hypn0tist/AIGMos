from __future__ import annotations

import shlex

from system.cs.lib.file_export import export_text
from system.cs.parser import HandlerResponse


command = "export.file"
help_short = "export.file <src> <dst>"
help_full = (
    "export.file <src> <dst>\n"
    "\n"
    "Examples:\n"
    "  export.file $MEM:file ./out.txt\n"
    "  export.file #notes:summary ./summary.txt\n"
    "  export.file $MEM:file $MEM:path\n"
    "\n"
    "Semantics:\n"
    "- src first\n"
    "- dst second\n"
    "- src must resolve to one string leaf\n"
    "- dst may be literal filesystem path or symbol containing path\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"export.file parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: export.file <src> <dst>")

    _, src, dst = parts

    try:
        export_text(parser, src, dst)
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
