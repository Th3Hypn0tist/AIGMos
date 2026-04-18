# system/cs/commands/import_code.py

from __future__ import annotations

import shlex

from system.cs.lib.file_import import import_code_tree, resolve_source_path, validate_code_root
from system.cs.parser import HandlerResponse


command = "import.code"
help_short = "import.code <src> <dst>"
help_full = (
    "import.code <src> <dst>\n"
    "\n"
    "Examples:\n"
    "  import.code ./system #code\n"
    "  import.code ./main.py #code\n"
    "  import.code $MEM:srcpath #code\n"
    "\n"
    "Semantics:\n"
    "- src first\n"
    "- dst last\n"
    "- src may be literal filesystem path or symbol containing path\n"
    "- src may be a file or directory\n"
    "- dst must be # root\n"
    "- file import => #root:<filename>\n"
    "- dir import  => #root:<relative:path>\n"
    "- clears existing dst subtree first\n"
    "- reads ignore patterns from #SYSTEM:config:import:code:ignore:<n>\n"
)


def handler(line: str, parser) -> HandlerResponse:
    try:
        parts = shlex.split(line)
    except Exception as exc:
        return HandlerResponse(error=f"import.code parse error: {exc}")

    if len(parts) != 3:
        return HandlerResponse(error="usage: import.code <src> <dst>")

    _, src_token, dst_root = parts

    try:
        validate_code_root(dst_root)
        src_path = resolve_source_path(parser, src_token)
        import_code_tree(parser, src_path, dst_root)
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")
