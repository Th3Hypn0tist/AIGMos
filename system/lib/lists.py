# system/lib/lists.py
# Store-based primitives (no Core dependency).
# store shape: store[root][sub] = list

def sub_ls(store, root):
    return sorted(store[root].keys())

def sub_mk(store, root, sub):
    store[root].setdefault(sub, [])
    return "OK"

def sub_rm(store, root, sub):
    store[root].pop(sub, None)
    return "OK"

def items_ls(store, root, sub):
    return list(store[root][sub])

def item_append(store, root, sub, value):
    store[root][sub].append(value)
    return "OK"

def item_get(store, root, sub, idx: int):
    return store[root][sub][idx]

def item_set(store, root, sub, idx: int, value):
    store[root][sub][idx] = value
    return "OK"

def item_del(store, root, sub, idx: int):
    return store[root][sub].pop(idx)

def item_clear(store, root, sub):
    store[root][sub] = []
    return "OK"
