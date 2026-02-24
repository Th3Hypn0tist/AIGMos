# system/lib/tables.py
# Store-based primitives (no Core dependency).
#
# Store shape:
#   store[root] is a dict representing the top of an infinite tree.
#   Each node is either:
#     - dict (branch)
#     - scalar (leaf)  (usually str)
#
# Used by topics (runner/events/io/planner) without importing surface.py.

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _root_dict(store: Dict[str, Any], root: str) -> Dict[str, Any]:
    store.setdefault(root, {})
    r = store[root]
    if not isinstance(r, dict):
        r = {}
        store[root] = r
    return r


def node_get(store: Dict[str, Any], root: str, path: List[str]) -> Any:
    cur: Any = _root_dict(store, root)
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def node_ensure_dict(store: Dict[str, Any], root: str, path: List[str]) -> Dict[str, Any]:
    cur: Any = _root_dict(store, root)
    for p in path:
        nxt = cur.get(p)
        if nxt is None:
            nxt = {}
            cur[p] = nxt
        elif not isinstance(nxt, dict):
            raise ValueError(f"Path collision at '{p}'")
        cur = nxt
    return cur


def node_ls(store: Dict[str, Any], root: str, path: List[str]) -> List[str]:
    node = node_get(store, root, path)
    if not isinstance(node, dict):
        raise ValueError("ls expects dict node")
    return sorted(node.keys())


def leaf_set(store: Dict[str, Any], root: str, path: List[str], text: str) -> None:
    if not path:
        raise ValueError("Empty # path")
    parent = node_ensure_dict(store, root, path[:-1])
    k = path[-1]
    cur = parent.get(k)
    if isinstance(cur, dict):
        raise ValueError("Cannot overwrite dict node with scalar")
    parent[k] = text


def leaf_append(store: Dict[str, Any], root: str, path: List[str], text: str) -> None:
    if not path:
        raise ValueError("Empty # path")
    parent = node_ensure_dict(store, root, path[:-1])
    k = path[-1]
    cur = parent.get(k, "")
    if isinstance(cur, dict):
        raise ValueError("Cannot overwrite dict node with scalar")
    parent[k] = (str(cur) + text) if cur else text


def node_rm(store: Dict[str, Any], root: str, path: List[str]) -> bool:
    if not path:
        raise ValueError("Empty # path")
    parent = node_get(store, root, path[:-1]) if len(path) > 1 else _root_dict(store, root)
    if not isinstance(parent, dict):
        return False
    return parent.pop(path[-1], None) is not None


def node_set(store: Dict[str, Any], root: str, path: List[str], node: Any) -> None:
    if not path:
        raise ValueError("Empty # path")
    parent = node_ensure_dict(store, root, path[:-1])
    k = path[-1]
    parent[k] = node


def walk_leaves(store: Dict[str, Any], root: str, base_path: List[str]) -> List[Tuple[List[str], str]]:
    """Return (path_tokens, leaf_text) for all leaves under base_path, sorted by path."""
    start = node_get(store, root, base_path)
    if start is None:
        return []
    out: List[Tuple[List[str], str]] = []

    def rec(cur_path: List[str], node: Any):
        if isinstance(node, dict):
            for k in sorted(node.keys()):
                rec(cur_path + [k], node[k])
        else:
            out.append((cur_path, str(node)))

    rec(list(base_path), start)
    out.sort(key=lambda t: tuple(t[0]))
    return out
