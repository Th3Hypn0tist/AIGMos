# system/topics/texts.py
#
# Authoring helpers for texts store.
# Root is LOCKED to kvlists root "texts".
#
# These commands are INTERNAL (sys.*). User reaches them only via aliases.

from system.lib import kvlists as kvl

TEXTS_ROOT = "texts"

def key_ensure(core, sub, key):
    kvl_store = getattr(core, 'kvl', core.state['kvlists'])
    core._require_kv_root(TEXTS_ROOT)
    # create sub if missing
    kvl.sub_mk(kvl_store, TEXTS_ROOT, sub)
    # ensure key exists with empty string if missing
    if key not in kvl_store[TEXTS_ROOT][sub]:
        kvl.kv_set(kvl_store, TEXTS_ROOT, sub, key, "")
    return "OK"

def text_append(core, sub, key, *text_parts):
    kvl_store = getattr(core, 'kvl', core.state['kvlists'])
    core._require_kv_root(TEXTS_ROOT)
    kvl.sub_mk(kvl_store, TEXTS_ROOT, sub)
    cur = kvl_store[TEXTS_ROOT][sub].get(key, "")
    add = " ".join(text_parts)
    newv = (cur + add) if cur else add
    kvl.kv_set(kvl_store, TEXTS_ROOT, sub, key, newv)
    return "OK"

COMMANDS = {
    "sys.t.key.ensure":  (key_ensure,  "Ensure empty key under texts/<sub>", "sys.t.key.ensure <sub> <key>"),
    "sys.t.text.append": (text_append, "Append text to texts/<sub>/<key>",   "sys.t.text.append <sub> <key> <text...>"),
}
