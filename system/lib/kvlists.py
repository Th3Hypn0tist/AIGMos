# system/lib/kvlists.py
# Store-based primitives (no Core dependency).
# store shape: store[root][sub][key] = scalar

def sub_ls(store, root):
    return sorted(store[root].keys())

def sub_mk(store, root, sub):
    store[root].setdefault(sub, {})
    return "OK"

def sub_rm(store, root, sub):
    store[root].pop(sub, None)
    return "OK"

def kv_ls(store, root, sub):
    return sorted(store[root][sub].keys())

def kv_set(store, root, sub, key, value):
    store[root][sub][key] = value
    return "OK"

def kv_get(store, root, sub, key):
    return store[root][sub].get(key)

def kv_del(store, root, sub, key):
    return store[root][sub].pop(key, None)

def kv_clear(store, root, sub):
    store[root][sub] = {}
    return "OK"
