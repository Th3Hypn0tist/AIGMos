# system/topics/kvlists.py

def roots_ls(core):
    return sorted(core.kv_roots)

def sub_ls(core, root):
    core._require_kv_root(root)
    return sorted(core.state["kvlists"][root].keys())

def sub_mk(core, root, sub):
    core._require_kv_root(root)
    core.state["kvlists"][root].setdefault(sub, {})
    return "OK"

def sub_rm(core, root, sub):
    core._require_kv_sub(root, sub)
    del core.state["kvlists"][root][sub]
    return "OK"

def sub_keys(core, root):
    core._require_kv_root(root)
    return sorted(core.state["kvlists"][root].keys())

def kv_ls(core, root, sub):
    core._require_kv_sub(root, sub)
    return sorted(core.state["kvlists"][root][sub].keys())

def kv_set(core, root, sub, key, *value_parts):
    core._require_kv_sub(root, sub)
    core.state["kvlists"][root][sub][key] = " ".join(value_parts)
    return "OK"

def kv_get(core, root, sub, key):
    core._require_kv_sub(root, sub)
    return core.state["kvlists"][root][sub].get(key)

def kv_del(core, root, sub, key):
    core._require_kv_sub(root, sub)
    d = core.state["kvlists"][root][sub]
    return d.pop(key, None)

def kv_clear(core, root, sub):
    core._require_kv_sub(root, sub)
    core.state["kvlists"][root][sub] = {}
    return "OK"


COMMANDS = {
    # roots
    "sys.kvl.ls":        (roots_ls, "List kvlists roots (schema anchors)", "sys.kvl.ls"),

    # subs
    "sys.kvl.sub.ls":    (sub_ls,   "List subs under kvlists root",             "sys.kvl.sub.ls <root>"),
    "sys.kvl.sub.mk":    (sub_mk,   "Create sub under kvlists root",            "sys.kvl.sub.mk <root> <sub>"),
    "sys.kvl.sub.rm":    (sub_rm,   "Remove sub under kvlists root (and keys)", "sys.kvl.sub.rm <root> <sub>"),
    "sys.kvl.sub.keys":  (sub_keys, "List sub-dict names under kvlists root",   "sys.kvl.sub.keys <root>"),

    # kv
    "sys.kvl.kv.ls":     (kv_ls,    "List keys under root/sub",                 "sys.kvl.kv.ls <root> <sub>"),
    "sys.kvl.kv.set":    (kv_set,   "Set key=value under root/sub",             "sys.kvl.kv.set <root> <sub> <key> <value...>"),
    "sys.kvl.kv.get":    (kv_get,   "Get value for key under root/sub",         "sys.kvl.kv.get <root> <sub> <key>"),
    "sys.kvl.kv.del":    (kv_del,   "Delete key under root/sub",                "sys.kvl.kv.del <root> <sub> <key>"),
    "sys.kvl.kv.clear":  (kv_clear, "Clear all keys under root/sub",            "sys.kvl.kv.clear <root> <sub>"),
}
