# system/topics/lists.py

def roots_ls(core):
    return sorted(core.list_roots)

def sub_ls(core, root):
    core._require_list_root(root)
    return sorted(core.state["lists"][root].keys())

def sub_mk(core, root, sub):
    core._require_list_root(root)
    core.state["lists"][root].setdefault(sub, [])
    return "OK"

def sub_rm(core, root, sub):
    core._require_list_sub(root, sub)
    del core.state["lists"][root][sub]
    return "OK"

def items_ls(core, root, sub):
    core._require_list_sub(root, sub)
    return list(core.state["lists"][root][sub])

def item_append(core, root, sub, *value_parts):
    core._require_list_sub(root, sub)
    core.state["lists"][root][sub].append(" ".join(value_parts))
    return "OK"

def item_get(core, root, sub, idx):
    core._require_list_sub(root, sub)
    i = int(idx)
    return core.state["lists"][root][sub][i]

def item_set(core, root, sub, idx, *value_parts):
    core._require_list_sub(root, sub)
    i = int(idx)
    core.state["lists"][root][sub][i] = " ".join(value_parts)
    return "OK"

def item_del(core, root, sub, idx):
    core._require_list_sub(root, sub)
    i = int(idx)
    return core.state["lists"][root][sub].pop(i)

def item_clear(core, root, sub):
    core._require_list_sub(root, sub)
    core.state["lists"][root][sub] = []
    return "OK"


COMMANDS = {
    # roots
    "sys.lst.ls":         (roots_ls,    "List lists roots (schema anchors)", "sys.lst.ls"),

    # subs
    "sys.lst.sub.ls":     (sub_ls,      "List subs under lists root",             "sys.lst.sub.ls <root>"),
    "sys.lst.sub.mk":     (sub_mk,      "Create sub under lists root",            "sys.lst.sub.mk <root> <sub>"),
    "sys.lst.sub.rm":     (sub_rm,      "Remove sub under lists root (and list)", "sys.lst.sub.rm <root> <sub>"),

    # items
    "sys.lst.items.ls":   (items_ls,    "List items under root/sub",              "sys.lst.items.ls <root> <sub>"),
    "sys.lst.item.append":(item_append, "Append item under root/sub",             "sys.lst.item.append <root> <sub> <value...>"),
    "sys.lst.item.get":   (item_get,    "Get item by index under root/sub",       "sys.lst.item.get <root> <sub> <idx>"),
    "sys.lst.item.set":   (item_set,    "Set item by index under root/sub",       "sys.lst.item.set <root> <sub> <idx> <value...>"),
    "sys.lst.item.del":   (item_del,    "Delete item by index under root/sub",    "sys.lst.item.del <root> <sub> <idx>"),
    "sys.lst.item.clear": (item_clear,  "Clear list under root/sub",              "sys.lst.item.clear <root> <sub>"),
}
