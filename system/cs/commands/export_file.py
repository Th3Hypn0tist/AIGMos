from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


from system.cs.command_args import parse_argv

from system.cs.lib.file_export import export_text


command = "export.file"
help_short = 'export.file <src> <dst>'
help_full = """export one resolved string value to filesystem path or symbol

current implementation:
- src first
- dst last
- src must resolve to exactly one string value

note:
- this help describes the current command implementation
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        _, src, dst = parse_argv(
            line,
            usage="usage: export.file <src> <dst>",
            label="export.file",
            exact=2,
        )
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        export_text(parser, src, dst)
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

