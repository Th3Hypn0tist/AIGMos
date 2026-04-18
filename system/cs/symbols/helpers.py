# system/cs/symbols/helpers.py

RUNNER_TOKENS = {"run", "wait", "once", "cycle", "loop"}


def parse_runner_control(line: str) -> dict | None:
    parts = line.split()
    if len(parts) != 2:
        return None

    target, token = parts
    if not target.startswith("%"):
        return None
    if token not in RUNNER_TOKENS:
        return None

    return {
        "kind": "runner_control",
        "target": target,
        "token": token,
        "raw": line,
    }
