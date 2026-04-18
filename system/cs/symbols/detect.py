# system/cs/symbols/detect.py

SYMBOL_ROOTS = "&%!$#@|"


def is_symbol_line(line: str) -> bool:
    if not isinstance(line, str):
        return False
    stripped = line.lstrip()
    return bool(stripped) and stripped[0] in SYMBOL_ROOTS


def symbol_root(line: str) -> str:
    stripped = line.lstrip()
    if not stripped:
        return ""
    return stripped[0]
