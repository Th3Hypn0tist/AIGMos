# system/cs/commands/export_code.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv

from system.cs.lib.file_export import export_code


command = "export.code"
help_short = 'export.code <src> <dst>'
help_full = """export code-like content from state to filesystem path or symbol

current implementation:
- src first
- dst last
- src may be $, #, or a code subtree
- dst may be a filesystem path or compatible symbol target

note:
- this help describes the current command implementation
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, src, dst = parse_argv(
            line,
            usage="usage: export.code <src> <dst>",
            label="export.code",
            exact=2,
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        export_code(parser, src, dst)
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

