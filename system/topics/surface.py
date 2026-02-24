# system/topics/surface.py
#
# Stage1 user-surface primitives (sys.*) behind aliases.
# Parses & / $ / % / # prefixes and routes to locked roots.
#
# Locked roots:
#   routines (lists root)   for &
#   texts    (kvlists root) for $
#   tables   (tables root)  for # (infinite dict store)

ROUTINES_ROOT = "routines"
TEXTS_ROOT = "texts"
TABLES_ROOT = "tables"


# ----------------- parsers -----------------

def _parse_amp(s: str) -> str:
    if not (isinstance(s, str) and s.startswith("&") and len(s) > 1):
        raise ValueError("Expected &<name>")
    return s[1:]


def _parse_dollar(s: str) -> str:
    if not (isinstance(s, str) and s.startswith("$") and len(s) > 1):
        raise ValueError("Expected $<sub> or $<sub>:<key>")
    return s[1:]


def _parse_pct(s: str) -> str:
    if not (isinstance(s, str) and s.startswith("%") and len(s) > 1):
        raise ValueError("Expected %<name>")
    return s[1:]


def _split_kv_target(tok: str):
    # $sub       -> (sub, None)
    # $sub:key   -> (sub, key)
    s = _parse_dollar(tok)
    if ":" in s:
        sub, key = s.split(":", 1)
        if not sub or not key:
            raise ValueError("Expected $<sub>:<key>")
        return sub, key
    return s, None


def _parse_hash(tok: str) -> list[str]:
    # #a:b:c  (infinite depth)
    if not (isinstance(tok, str) and tok.startswith("#") and len(tok) > 1):
        raise ValueError("Expected #<path>")
    parts = tok[1:].split(":")
    if any(p == "" for p in parts):
        raise ValueError("Invalid # path")
    return parts


# ----------------- tables store helpers -----------------

def _tables_root(core) -> dict:
    core.tables.setdefault(TABLES_ROOT, {})
    return core.tables[TABLES_ROOT]


def _table_ensure(root: dict, path: list[str]) -> dict:
    cur = root
    for p in path:
        nxt = cur.get(p)
        if nxt is None:
            nxt = {}
            cur[p] = nxt
        elif not isinstance(nxt, dict):
            raise ValueError(f"Path collision at '{p}'")
        cur = nxt
    return cur


def _table_get(root: dict, path: list[str]):
    cur = root
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _table_set_leaf_append(root: dict, path: list[str], text: str):
    if not path:
        raise ValueError("Empty # path")
    parent = _table_ensure(root, path[:-1])
    key = path[-1]
    cur = parent.get(key, "")
    if isinstance(cur, dict):
        raise ValueError("Cannot overwrite dict node with scalar")
    parent[key] = (str(cur) + text) if cur else text


def _table_rm(root: dict, path: list[str]):
    if not path:
        raise ValueError("Empty # path")
    parent = _table_get(root, path[:-1]) if len(path) > 1 else root
    if not isinstance(parent, dict):
        return False
    parent.pop(path[-1], None)
    return True


# ----------------- primitives -----------------

def mk(core, target):
    if target.startswith("&"):
        name = _parse_amp(target)
        core.l[ROUTINES_ROOT].setdefault(name, [])
        return "OK"

    if target.startswith("$"):
        sub, key = _split_kv_target(target)
        if key is not None:
            raise ValueError("mk expects $<sub> only (not $<sub>:<key>)")
        core.kvl[TEXTS_ROOT].setdefault(sub, {})
        return "OK"

    if target.startswith("#"):
        _table_ensure(_tables_root(core), _parse_hash(target))
        return "OK"

    raise ValueError("mk expects &<name> OR $<sub> OR #<path>")


def rm(core, target):
    if target.startswith("&"):
        name = _parse_amp(target)
        core._require_list_sub(ROUTINES_ROOT, name)
        del core.l[ROUTINES_ROOT][name]
        return "OK"

    if target.startswith("$"):
        sub, key = _split_kv_target(target)
        if key is not None:
            raise ValueError("rm expects $<sub> only (not $<sub>:<key>)")
        core._require_kv_sub(TEXTS_ROOT, sub)
        del core.kvl[TEXTS_ROOT][sub]
        return "OK"

    if target.startswith("#"):
        _table_rm(_tables_root(core), _parse_hash(target))
        return "OK"

    raise ValueError("rm expects &<name> OR $<sub> OR #<path>")


def ls(core, target=None):
    if target is None:
        return (
            "$  texts      (key/value symbol store)\n"
            "&  routines   (linear execution lists)\n"
            "#  tables     (infinite dict store)"
        )

    if target == "$":
        return sorted(core.kvl[TEXTS_ROOT].keys())

    if target == "&":
        return sorted(core.l[ROUTINES_ROOT].keys())

    if target.startswith("$"):
        sub, key = _split_kv_target(target)
        if key is not None:
            raise ValueError("ls expects $<sub> only (not $<sub>:<key>)")
        core._require_kv_sub(TEXTS_ROOT, sub)
        return sorted(core.kvl[TEXTS_ROOT][sub].keys())

    if target.startswith("&"):
        name = _parse_amp(target)
        core._require_list_sub(ROUTINES_ROOT, name)
        return list(core.l[ROUTINES_ROOT][name])

    if target.startswith("#"):
        val = _table_get(_tables_root(core), _parse_hash(target))
        if val is None:
            return ""
        if not isinstance(val, dict):
            raise ValueError("ls expects a dict node; use cat for leaf values")
        return "\n".join(sorted(val.keys()))

    raise ValueError("ls usage: ls | ls &<name> | ls $ | ls $<sub> | ls #<path>")


def add_item(core, target, *rest):
    if target.startswith("&"):
        name = _parse_amp(target)
        core._require_list_sub(ROUTINES_ROOT, name)
        step = " ".join(rest).strip()
        core.l[ROUTINES_ROOT][name].append(step)
        return "OK"

    if target.startswith("$"):
        sub, key = _split_kv_target(target)
        core.kvl[TEXTS_ROOT].setdefault(sub, {})
        if key is None:
            if len(rest) != 1:
                raise ValueError("add.item $<sub> expects exactly one <key>")
            k = rest[0]
            core.kvl[TEXTS_ROOT][sub].setdefault(k, "")
            return "OK"
        text = " ".join(rest).strip()
        cur = core.kvl[TEXTS_ROOT][sub].get(key, "")
        core.kvl[TEXTS_ROOT][sub][key] = (cur + text) if cur else text
        return "OK"

    if target.startswith("#"):
        text = " ".join(rest).strip()
        if not text:
            raise ValueError("add.item #<path> expects <text...>")
        _table_set_leaf_append(_tables_root(core), _parse_hash(target), text)
        return "OK"

    raise ValueError("add.item expects &... or $... or #...")


def cat(core, target):
    # ---- TEXTS ($sub:key) ----
    if target.startswith("$"):
        body = target[1:]
        if ":" not in body:
            raise ValueError("Expected $<sub>:<key>")
        sub, key = body.split(":", 1)
        core._require_kv_sub(TEXTS_ROOT, sub)

        value = core.kvl[TEXTS_ROOT][sub].get(key)
        if value is None:
            raise ValueError("Key not found")
        return str(value)

    # ---- ROUTINES (&name) ----
    if target.startswith("&"):
        name = _parse_amp(target)
        core._require_list_sub(ROUTINES_ROOT, name)
        return "\n".join(str(x) for x in core.l[ROUTINES_ROOT][name])

    # ---- TABLES (#path) ----
    if target.startswith("#"):
        val = _table_get(_tables_root(core), _parse_hash(target))
        if val is None:
            return ""
        if isinstance(val, dict):
            raise ValueError("cat expects a leaf; use ls for dict nodes")
        return str(val)

    raise ValueError("cat expects $... or &... or #...")


# ----------------- CP + MV (existing semantics, unchanged) -----------------

def _deep_clone_tree(node):
    # node can be dict or scalar
    if isinstance(node, dict):
        return {k: _deep_clone_tree(v) for k, v in node.items()}
    return node


def cp(core, src: str, dst: str):
    # ------------------------------------------------------------
    # # -> #  (subtree clone, overwrite)
    # ------------------------------------------------------------
    if src.startswith("#") and dst.startswith("#"):
        s_path = _parse_hash(src)
        d_path = _parse_hash(dst)

        s_val = _table_get(_tables_root(core), s_path)
        if s_val is None:
            raise ValueError("Source #path not found")

        d_parent = _table_ensure(_tables_root(core), d_path[:-1]) if len(d_path) > 1 else _tables_root(core)
        d_key = d_path[-1]
        d_parent[d_key] = _deep_clone_tree(s_val)
        return "OK"

    # ------------------------------------------------------------
    # $ -> #  (dict -> dict): cp $sub #path  (whole sub)
    # $ -> #  (leaf -> leaf): cp $sub:key #path
    # ------------------------------------------------------------
    if src.startswith("$") and dst.startswith("#"):
        s_sub, s_key = _split_kv_target(src)
        d_path = _parse_hash(dst)

        if s_key is None:
            core._require_kv_sub(TEXTS_ROOT, s_sub)
            subdict = core.kvl[TEXTS_ROOT][s_sub]  # key -> scalar

            d_parent = _table_ensure(_tables_root(core), d_path[:-1]) if len(d_path) > 1 else _tables_root(core)
            d_key = d_path[-1]
            d_parent[d_key] = {k: v for k, v in subdict.items()}
            return "OK"

        core._require_kv_sub(TEXTS_ROOT, s_sub)
        if s_key not in core.kvl[TEXTS_ROOT][s_sub]:
            raise ValueError("Source key not found")

        d_parent = _table_ensure(_tables_root(core), d_path[:-1]) if len(d_path) > 1 else _tables_root(core)
        d_key = d_path[-1]
        d_parent[d_key] = core.kvl[TEXTS_ROOT][s_sub][s_key]
        return "OK"

    # ------------------------------------------------------------
    # # -> $  (dict -> dict): cp #path $sub  (whole subtree -> sub)
    # # -> $  (leaf -> leaf): cp #path $sub:key
    # ------------------------------------------------------------
    if src.startswith("#") and dst.startswith("$"):
        s_path = _parse_hash(src)
        d_sub, d_key = _split_kv_target(dst)

        s_val = _table_get(_tables_root(core), s_path)
        if s_val is None:
            raise ValueError("Source #path not found")

        if d_key is None:
            if not isinstance(s_val, dict):
                raise ValueError("cp #-> $sub expects #path to be a dict node")

            for k, v in s_val.items():
                if isinstance(v, dict):
                    raise ValueError("Cannot import nested dict into $sub (expected flat dict of scalars)")

            core.kvl[TEXTS_ROOT].setdefault(d_sub, {})
            core.kvl[TEXTS_ROOT][d_sub] = {k: v for k, v in s_val.items()}
            return "OK"

        if isinstance(s_val, dict):
            raise ValueError("cp #leaf -> $sub:key requires #path to be a leaf value")

        core.kvl[TEXTS_ROOT].setdefault(d_sub, {})
        core.kvl[TEXTS_ROOT][d_sub][d_key] = str(s_val)
        return "OK"

    # ------------------------------------------------------------
    # & -> #  (ONLY one step): cp &name:idx #path
    # ------------------------------------------------------------
    if src.startswith("&") and dst.startswith("#"):
        body = src[1:]
        if ":" not in body:
            raise ValueError("cp &-># supports only one step: cp &name:<idx> #path")
        name, idx_s = body.split(":", 1)
        if not idx_s.isdigit():
            raise ValueError("Index must be integer")
        idx = int(idx_s)

        d_path = _parse_hash(dst)

        core._require_list_sub(ROUTINES_ROOT, name)
        steps = core.l[ROUTINES_ROOT][name]
        if idx < 0 or idx >= len(steps):
            raise ValueError("Step index out of range")

        d_parent = _table_ensure(_tables_root(core), d_path[:-1]) if len(d_path) > 1 else _tables_root(core)
        d_key = d_path[-1]
        d_parent[d_key] = str(steps[idx])
        return "OK"

    # ------------------------------------------------------------
    # # -> &  (ONLY one leaf): cp #path &name        (append)
    #                         cp #path &name:idx     (overwrite/append-at-end)
    # ------------------------------------------------------------
    if src.startswith("#") and dst.startswith("&"):
        s_path = _parse_hash(src)
        s_val = _table_get(_tables_root(core), s_path)
        if s_val is None:
            raise ValueError("Source #path not found")
        if isinstance(s_val, dict):
            raise ValueError("cp #->& requires #path to be a leaf value")

        body = dst[1:]
        if not body:
            raise ValueError("Expected &<name> or &<name>:<idx>")

        if ":" in body:
            name, idx_s = body.split(":", 1)
            if not idx_s.isdigit():
                raise ValueError("Index must be integer")
            idx = int(idx_s)
        else:
            name, idx = body, None

        core._require_list_sub(ROUTINES_ROOT, name)
        steps = core.l[ROUTINES_ROOT][name]
        val = str(s_val)

        if idx is None:
            steps.append(val)
            return "OK"

        if idx < 0 or idx > len(steps):
            raise ValueError("Index out of range")
        if idx == len(steps):
            steps.append(val)
        else:
            steps[idx] = val
        return "OK"

    # ------------------------------------------------------------
    # EXISTING: $ <-> $ , $ <-> & , & <-> $ , & <-> &
    # ------------------------------------------------------------

    # $ -> $ (all levels)
    if src.startswith("$") and dst.startswith("$"):
        s_sub, s_key = _split_kv_target(src)
        d_sub, d_key = _split_kv_target(dst)

        if s_key is None and d_key is None:
            core._require_kv_sub(TEXTS_ROOT, s_sub)
            core.kvl[TEXTS_ROOT].setdefault(d_sub, {})
            # overwrite whole sub (clone)
            core.kvl[TEXTS_ROOT][d_sub] = dict(core.kvl[TEXTS_ROOT][s_sub])
            return "OK"

        if s_key is not None and d_key is not None:
            core._require_kv_sub(TEXTS_ROOT, s_sub)
            if s_key not in core.kvl[TEXTS_ROOT][s_sub]:
                raise ValueError("Source key not found")
            core.kvl[TEXTS_ROOT].setdefault(d_sub, {})
            core.kvl[TEXTS_ROOT][d_sub][d_key] = core.kvl[TEXTS_ROOT][s_sub][s_key]
            return "OK"

        raise ValueError("cp $->$ requires same level: $sub->$sub or $sub:key->$sub:key")

    # $ -> & (one key only; append if no index)
    if src.startswith("$") and dst.startswith("&"):
        s_sub, s_key = _split_kv_target(src)
        if s_key is None:
            raise ValueError("cp $->& supports only one key: cp $sub:key &name[[:idx]]")

        body = dst[1:]
        if not body:
            raise ValueError("Expected &<name> or &<name>:<idx>")

        if ":" in body:
            name, idx_s = body.split(":", 1)
            if not idx_s.isdigit():
                raise ValueError("Index must be integer")
            idx = int(idx_s)
        else:
            name, idx = body, None

        core._require_list_sub(ROUTINES_ROOT, name)
        core._require_kv_sub(TEXTS_ROOT, s_sub)

        if s_key not in core.kvl[TEXTS_ROOT][s_sub]:
            raise ValueError("Source key not found")

        val = str(core.kvl[TEXTS_ROOT][s_sub][s_key])
        steps = core.l[ROUTINES_ROOT][name]

        if idx is None:
            steps.append(val)  # append
            return "OK"

        # indexed write: overwrite (or append if idx == len)
        if idx < 0 or idx > len(steps):
            raise ValueError("Index out of range")
        if idx == len(steps):
            steps.append(val)
        else:
            steps[idx] = val
        return "OK"

    # & -> $ (one step only)
    if src.startswith("&") and dst.startswith("$"):
        body = src[1:]
        if ":" not in body:
            raise ValueError("cp &->$ supports only one step: cp &name:<idx> $sub:key")
        name, idx_s = body.split(":", 1)
        if not idx_s.isdigit():
            raise ValueError("Index must be integer")
        idx = int(idx_s)

        d_sub, d_key = _split_kv_target(dst)
        if d_key is None:
            raise ValueError("cp &->$ requires $sub:key")

        core._require_list_sub(ROUTINES_ROOT, name)
        steps = core.l[ROUTINES_ROOT][name]
        if idx < 0 or idx >= len(steps):
            raise ValueError("Step index out of range")

        core.kvl[TEXTS_ROOT].setdefault(d_sub, {})
        core.kvl[TEXTS_ROOT][d_sub][d_key] = str(steps[idx])
        return "OK"

    # & -> & (whole routine copy)
    if src.startswith("&") and dst.startswith("&"):
        s_name = _parse_amp(src)
        d_name = _parse_amp(dst)

        core._require_list_sub(ROUTINES_ROOT, s_name)
        core.l[ROUTINES_ROOT].setdefault(d_name, [])
        core.l[ROUTINES_ROOT][d_name] = list(core.l[ROUTINES_ROOT][s_name])  # overwrite clone
        return "OK"

    raise ValueError("cp supports $->$, $->&, &->$, &->&, plus $<->#, &<->#, #->#")

def mv(core, src: str, dst: str):
    if src == dst:
        return "Need coffee?"

    # ------------------------------------------------------------
    # # -> #  (subtree move, overwrite)
    # ------------------------------------------------------------
    if src.startswith("#") and dst.startswith("#"):
        s_path = _parse_hash(src)
        d_path = _parse_hash(dst)

        root = _tables_root(core)

        s_parent = _table_get(root, s_path[:-1]) if len(s_path) > 1 else root
        if not isinstance(s_parent, dict) or s_path[-1] not in s_parent:
            raise ValueError("Source #path not found")

        node = s_parent.pop(s_path[-1])  # dict or scalar

        d_parent = _table_ensure(root, d_path[:-1]) if len(d_path) > 1 else root
        d_parent[d_path[-1]] = node
        return "OK"

    # ------------------------------------------------------------
    # $ -> $ (same namespace only)
    # ------------------------------------------------------------
    if src.startswith("$") and dst.startswith("$"):
        s_sub, s_key = _split_kv_target(src)
        d_sub, d_key = _split_kv_target(dst)

        core._require_kv_sub(TEXTS_ROOT, s_sub)
        core.kvl[TEXTS_ROOT].setdefault(d_sub, {})

        # move whole sub (rename)
        if s_key is None and d_key is None:
            core.kvl[TEXTS_ROOT][d_sub] = core.kvl[TEXTS_ROOT].pop(s_sub)
            return "OK"

        # move single key
        if s_key is not None and d_key is not None:
            if s_key not in core.kvl[TEXTS_ROOT][s_sub]:
                raise ValueError("Source key not found")
            val = core.kvl[TEXTS_ROOT][s_sub].pop(s_key)
            core.kvl[TEXTS_ROOT][d_sub][d_key] = val
            return "OK"

        raise ValueError("mv $->$ requires same level: $sub->$sub or $sub:key->$sub:key")

    # ------------------------------------------------------------
    # & -> & (same namespace only)
    # ------------------------------------------------------------
    if src.startswith("&") and dst.startswith("&"):
        def _parse_amp_idx(tok: str):
            body = tok[1:]
            if not body:
                raise ValueError("Expected &<name> or &<name>:<idx>")
            if ":" in body:
                name, idx_s = body.split(":", 1)
                if not idx_s.isdigit():
                    raise ValueError("Index must be integer")
                return name, int(idx_s)
            return body, None

        s_name, s_idx = _parse_amp_idx(src)
        d_name, d_idx = _parse_amp_idx(dst)

        core._require_list_sub(ROUTINES_ROOT, s_name)
        core.l[ROUTINES_ROOT].setdefault(d_name, [])

        # move whole routine (rename)
        if s_idx is None and d_idx is None:
            core.l[ROUTINES_ROOT][d_name] = core.l[ROUTINES_ROOT].pop(s_name)
            return "OK"

        # move one step (overwrite / append-at-end)
        if s_idx is not None and d_idx is not None:
            steps = core.l[ROUTINES_ROOT][s_name]
            if s_idx < 0 or s_idx >= len(steps):
                raise ValueError("Source index out of range")

            step = steps.pop(s_idx)
            dst_steps = core.l[ROUTINES_ROOT][d_name]

            if d_idx < 0 or d_idx > len(dst_steps):
                raise ValueError("Destination index out of range")

            if d_idx == len(dst_steps):
                dst_steps.append(step)
            else:
                dst_steps[d_idx] = step

            return "OK"

        raise ValueError("mv &->& requires same level: &name->&name or &name:idx->&name:idx")

    raise ValueError("mv supports $->$, &->&, and #-># only")


COMMANDS = {
    "sys.mk":       (mk,       "Create a routine (&), text namespace ($), or table path (#)", "sys.mk &<name> | sys.mk $<sub> | sys.mk #<path>"),
    "sys.rm":       (rm,       "Remove a routine (&), text namespace ($), or table node (#)", "sys.rm &<name> | sys.rm $<sub> | sys.rm #<path>"),
    "sys.ls":       (ls,       "List routines, steps, text namespaces/keys, or table keys", "sys.ls [ &<name> | $ | $<sub> | #<path> ]"),
    "sys.add.item": (add_item, "Add routine step, write/append text key, or write/append table leaf", "sys.add.item &<name> <step...> | sys.add.item $<sub> <key> | sys.add.item $<sub>:<key> <text...> | sys.add.item #<path> <text...>"),
    "sys.cat":      (cat,      "Show the contents of a $ key, & routine, or # leaf", "sys.cat (&<name> | $<sub>:<key> | #<path>)"),
      "sys.cp":     (cp,
        "Copy between $, &, and #. Dict<->dict supports subtree clone.",
        (
            "sys.cp <src> <dst>\n"
            "  $<sub>            <-> #<path>        (subtree clone)\n"
            "  $<sub>:<key>      <-> #<path>        (leaf)\n"
            "  &<name>:<idx>      -> #<path>        (one step)\n"
            "  #<path>            -> &<name>[:idx]  (one leaf; append if no idx)\n"
            "  #<src>             -> #<dst>         (subtree clone)\n"
            "  (existing: $<->$, $<->&, &<->$, &<->&)"
        )
    ),
    "sys.mv": (mv,
        "Move/rename within $ (texts), within & (routines), or within # (tables/tree). No cross moves.",
        (
        "sys.mv <src> <dst>\n"
        "  $<sub>            -> $<sub>            (rename namespace)\n"
        "  $<sub>:<key>      -> $<sub>:<key>      (move key)\n"
        "  &<name>           -> &<name>           (rename routine)\n"
        "  &<name>:<idx>     -> &<name>:<idx>     (move one step)\n"
        "  #<path>           -> #<path>           (move/rename subtree or leaf)\n"
        "  (no cross moves: $<>&, $<>#, &<># are rejected)"
        )
    ),
}
