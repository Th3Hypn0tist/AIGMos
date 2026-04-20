# system/cs/commands/import_list.py

from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse


import csv
from pathlib import Path

from system.cs.command_args import parse_argv
from system.cs.lib.ops import list_symbols
from system.cs.state_ops import delete_result, get_optional, set_result
from system.cs.symbol_rules import require_symbol

command = "import.list"
help_short = 'import.list <source> <target>'
help_full = """helper: import list-like text into an & target

rules:
- source may be a file path or symbol
- target must be an & list

note:
- import.list is a helper and not part of the v40 locked canonical command surface
"""

def _is_symbol(token: str) -> bool:
    return isinstance(token, str) and bool(token) and token[0] in "$#&%@!|"


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    raise ValueError(f"unable to decode file: {path}")


def _read_source_text(parser, source: str) -> str:
    if _is_symbol(source):
        value = get_optional(parser.state, source)
        if value is None:
            raise ValueError(f"source symbol not found: {source}")
        return str(value)

    path = Path(str(source)).expanduser()
    if not path.exists():
        raise ValueError(f"source path not found: {path}")
    if not path.is_file():
        raise ValueError(f"source is not a file: {path}")

    return _read_text_file(path)


def _clear_target_if_exists(parser, target: str) -> None:
    matches = [
        symbol
        for symbol in list_symbols(parser.state)
        if symbol == target
        or symbol.startswith(target + ":")
        or symbol.startswith(target + ".")
    ]

    for symbol in sorted(matches, key=len, reverse=True):
        delete_result(parser.state, symbol, writer="parser:import.list", op="import_list_clear_target")


def _row_to_item(row: list[str]) -> str:
    cells = [str(cell).strip() for cell in row]
    cells = [cell for cell in cells if cell != ""]
    return " ".join(cells)


def handler(line: str, parser) -> HandlerResponse:
    try:
        _, source, target = parse_argv(
            line,
            usage="usage: import.list <source> <target>",
            label="import.list",
            exact=2,
        )
        require_symbol(target, allowed="&", role="import.list target")
        text = _read_source_text(parser, source)

        if ";" not in text:
            return HandlerResponse(error=str('source is not semicolon-separated csv' or ""))

        rows = list(csv.reader(text.splitlines(), delimiter=";"))

        items: list[str] = []
        for row in rows:
            item = _row_to_item(row)
            if item:
                items.append(item)

        if not items:
            return HandlerResponse(error=str('source does not contain any usable ;-csv rows' or ""))

        _clear_target_if_exists(parser, target)
        set_result(parser.state, target, items, writer="parser:import.list", op="import_list_set_target")

    except Exception as exc:
        return HandlerResponse(error=str(str(exc) or ""))

    return HandlerResponse(buffer_output=str(f'import.list: imported {len(items)} rows -> {target}' or ""))

def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )

