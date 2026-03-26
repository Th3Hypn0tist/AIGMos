# system/cs/lib/state_tree.py

from __future__ import annotations

import json


_VALUE_KEY = "__value__"


def collect_branch_tree(parser, root: str):
    prefix = root + ":"

    listed = parser.state.list_symbols()
    if listed["error"]:
        raise RuntimeError(listed["error"])

    symbols = listed["result"] or []
    matches = sorted(s for s in symbols if s.startswith(prefix))
    if not matches:
        return None

    tree = {}

    for symbol in matches:
        got = parser.state.get(symbol)
        if got["error"]:
            raise RuntimeError(got["error"])

        value = got["result"]
        rel = symbol[len(prefix):]
        parts = rel.split(":")

        cur = tree
        for part in parts[:-1]:
            nxt = cur.get(part)

            if nxt is None:
                nxt = {}
                cur[part] = nxt
            elif not isinstance(nxt, dict):
                nxt = {_VALUE_KEY: nxt}
                cur[part] = nxt

            cur = nxt

        leaf = parts[-1]
        existing = cur.get(leaf)

        if isinstance(existing, dict):
            existing[_VALUE_KEY] = value
        elif existing is not None:
            cur[leaf] = {_VALUE_KEY: existing}
            cur[leaf][_VALUE_KEY] = value
        else:
            cur[leaf] = value

    return tree


def resolve_exact_or_branch(parser, target: str):
    out = parser.state.get(target)
    if out["error"]:
        raise RuntimeError(out["error"])

    exact = out["result"]
    branch = collect_branch_tree(parser, target)

    if exact is None:
        return branch

    if branch is None:
        return exact

    if isinstance(branch, dict):
        if _VALUE_KEY in branch:
            branch[_VALUE_KEY] = exact
        else:
            branch = {_VALUE_KEY: exact, **branch}
        return branch

    return exact


def dump_value(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)
