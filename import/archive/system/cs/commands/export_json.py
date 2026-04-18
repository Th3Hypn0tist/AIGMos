# system/cs/commands/export_json.py

from __future__ import annotations

import shlex

from system.cs.lib.file_export import export_json
from system.cs.parser import HandlerResponse


command = "export.json"
help_short = "export.json <src> <dst>"
help_full = (
    "export.json <src> <dst>\n"
    "\n"
    "Examples:\n"
    "  export.json #code ./code.json\n"
    "  export.json $MEM:data $MEM:path\n"
    "  export.json &jobs ./jobs.json\n"
    "\n"
    "Semantics:\n"
    "- src first\n"
    "- dst second\n"
    "- src must be state-side symbol\n"
    "- dst may be literal filesystem path or symbol containing path\n"
    "- writes JSON file\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"export.json parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: export.json <src> <dst>")

    _, src, dst = parts

    try:
        export_json(parser, src, dst)
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
