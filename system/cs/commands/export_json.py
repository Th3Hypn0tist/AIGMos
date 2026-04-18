from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import json
from pathlib import Path

from system.cs.command_args import parse_argv
from system.lib.symbols import resolve_raw_exact, validate_symbol, write_symbol_value


command = "export.json"
help_short = 'export.json <src> <dst>'
help_full = """export structured state as JSON text

current implementation:
- src first
- dst last
- src may be $, &, or #
- dst may be a file path or compatible symbol target

note:
- this help describes the current command implementation
"""

def handler(line: str, parser):
    try:
        _, src, dst = parse_argv(line, usage="usage: export.json <src> <dst>", label="export.json", exact=2)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    try:
        validate_symbol(src, allow_bare_root=False)
        payload = resolve_raw_exact(parser.state, src)
        if payload is None:
            raise ValueError("source not found")
        json_text = json.dumps(payload, ensure_ascii=False)

        if _looks_like_symbol(dst):
            validate_symbol(dst, allow_bare_root=False)
            write_symbol_value(parser.state, dst, json_text, writer="parser:export.json", op="export_json_symbol")
        else:
            _write_json_to_file(dst, json_text)
    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str('[ok]' or ""))


def _looks_like_symbol(text: str) -> bool:
    raw = str(text or "").strip()
    return bool(raw) and raw[0] in "$#&%!@|"


def _write_json_to_file(dst: str, json_text: str) -> None:
    path = Path(str(dst).strip()).expanduser()
    if not str(path):
        raise ValueError("destination path cannot be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_text, encoding="utf-8")

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

