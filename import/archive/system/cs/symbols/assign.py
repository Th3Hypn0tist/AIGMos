# system/cs/symbols/assign.py

from .detect import symbol_root


def parse_assignment(line: str) -> dict:
    if "=" not in line:
        raise ValueError(f"not an assignment: {line!r}")

    left, right = line.split("=", 1)
    target = left.strip()
    value = right.strip()

    if not target:
        raise ValueError(f"missing assignment target: {line!r}")

    return {
        "kind": "assign",
        "root": symbol_root(target),
        "target": target,
        "op": "=",
        "value": value,
        "raw": line,
    }
