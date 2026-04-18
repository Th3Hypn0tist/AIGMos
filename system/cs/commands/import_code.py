# system/cs/commands/import_code.py
from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import shlex

from system.cs.lib.file_import import import_code_tree, resolve_source_path, validate_code_root


command = "import.code"
help_short = 'import.code <src> <dst>'
help_full = """import one file or directory tree into # code structure

current implementation:
- src first
- dst last
- src may be literal path or symbol containing a path
- dst must be a # root
- existing dst subtree is cleared first

note:
- this help describes the current command implementation
"""

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
        import_code_tree(parser, src_path, dst_root, writer="parser:import.code")
    except Exception as exc:
        return HandlerResponse(error=str(exc))

    return HandlerResponse(buffer_output="[ok]")

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

