# system/topics/planner.py
#
# POC-MVP Planner (no LLM): shard a large task under any #root into parts.
# Planner has no side effects outside writing #root:plan.
#
# Commands (aliases expected):
#   plan <#root> <intent...> [max_files=N]
#   plan.show <#root>
#   plan.rm <#root>

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from system.lib import tables as tbl

TABLES_ROOT = "tables"


def _parse_hash(tok: str) -> List[str]:
    if not (isinstance(tok, str) and tok.startswith("#") and len(tok) > 1):
        raise ValueError("Expected #<path>")
    parts = tok[1:].split(":")
    if any(p == "" for p in parts):
        raise ValueError("Invalid # path")
    return parts


def _parse_kv_arg(arg: str) -> Tuple[str, str]:
    if "=" not in arg:
        raise ValueError("Expected key=value")
    k, v = arg.split("=", 1)
    if not k:
        raise ValueError("Invalid key")
    return k.strip(), v.strip()


def _leaf_count(core, root_tokens: List[str]) -> int:
    return len(tbl.walk_leaves(core.tables, TABLES_ROOT, root_tokens))


def _top_level_keys(core, root_tokens: List[str]) -> List[str]:
    node = tbl.node_get(core.tables, TABLES_ROOT, root_tokens)
    if node is None:
        return []
    if not isinstance(node, dict):
        return []
    return sorted(node.keys())


def plan(core, root_tok: str, *rest):
    if not root_tok.startswith("#"):
        raise ValueError("plan expects a #root")

    root_tokens = _parse_hash(root_tok)

    # defaults
    max_files = 25
    intent_parts: List[str] = []

    # parse rest: intent words + optional max_files=..
    for r in rest:
        if isinstance(r, str) and r.startswith("max_files="):
            _, v = _parse_kv_arg(r)
            if not v.isdigit():
                raise ValueError("max_files must be integer")
            max_files = int(v)
        else:
            intent_parts.append(r)

    intent = " ".join(intent_parts).strip()
    if not intent:
        raise ValueError("plan expects an intent string")

    # Strategy: S1 (top-level dirs) + S2 fallback (chunk by leaf count)
    shards: List[Dict[str, Any]] = []
    top = _top_level_keys(core, root_tokens)

    # if root missing, still write an empty plan (useful for scaffolding)
    if not top:
        doc = {
            "root": root_tokens,
            "intent": intent,
            "strategy": "S1+S2",
            "constraints": {"max_files": max_files},
            "shards": [],
        }
        tbl.leaf_set(core.tables, TABLES_ROOT, root_tokens + ["plan"], json.dumps(doc, indent=2))
        return "OK"

    sid = 1
    for k in top:
        subtree = root_tokens + [k]
        leaves = tbl.walk_leaves(core.tables, TABLES_ROOT, subtree)
        if len(leaves) <= max_files:
            shards.append({
                "id": f"{sid:02d}",
                "summary": f"{k}",
                "targets": [{"kind": "subtree", "path": [k]}],
                "leaf_count": len(leaves),
            })
            sid += 1
            continue

        # chunk this subtree by leaf paths
        leaf_paths = [pt for pt, _ in leaves]
        # convert to relative tokens under root (so user can apply under root)
        rel = [p[len(root_tokens):] for p in leaf_paths]
        # group by max_files
        for i in range(0, len(rel), max_files):
            chunk = rel[i:i+max_files]
            shards.append({
                "id": f"{sid:02d}",
                "summary": f"{k} (chunk {i//max_files+1})",
                "targets": [{"kind": "leafs", "paths": chunk}],
                "leaf_count": len(chunk),
            })
            sid += 1

    doc = {
        "root": root_tokens,
        "intent": intent,
        "strategy": "S1+S2",
        "constraints": {"max_files": max_files},
        "shards": shards,
    }

    tbl.leaf_set(core.tables, TABLES_ROOT, root_tokens + ["plan"], json.dumps(doc, indent=2))
    return "OK"


def plan_show(core, root_tok: str):
    root_tokens = _parse_hash(root_tok)
    node = tbl.node_get(core.tables, TABLES_ROOT, root_tokens + ["plan"])
    if node is None:
        return ""
    if isinstance(node, dict):
        raise ValueError("plan is not a leaf")
    return str(node)


def plan_rm(core, root_tok: str):
    root_tokens = _parse_hash(root_tok)
    tbl.node_rm(core.tables, TABLES_ROOT, root_tokens + ["plan"])
    return "OK"


COMMANDS = {
    "sys.plan": (plan, "Create a sharded plan under #root:plan", "plan #root <intent...> [max_files=N]"),
    "sys.plan.show": (plan_show, "Show #root:plan", "plan.show #root"),
    "sys.plan.rm": (plan_rm, "Remove #root:plan", "plan.rm #root"),
}
