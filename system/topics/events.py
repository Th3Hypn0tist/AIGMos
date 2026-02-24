# system/topics/events.py
#
# Numeric-only trigger bus + event bindings.
#
# Bindings:
#   ON <symbol.trg> <N> <command...>     (N is integer; N != 3)
#   ON.show <symbol.trg|*.trg>
#   ON.reset <symbol.trg|*.trg>
#
# Sources:
#   - %name.trg          (runner expander)
#   - $sub:key.trg       (text leaf ending with .trg; expanded here)
#   - #...:leaf.trg      (table leaf ending with .trg; expanded here)
#
# Latch:
#   one-shot per trigger symbol: fires once, re-arms only after trigger reads 0.
#
# Special:
#   trigger value 3 => purge bindings for that exact symbol (no commands executed)

import time
import threading

TEXTS_ROOT = "texts"


def _is_trg_symbol(sym: str) -> bool:
    return isinstance(sym, str) and sym.endswith(".trg")


def _match_pattern(sym: str, pat: str) -> bool:
    # 1.0 minimal patterns:
    # - exact match
    # - "*.trg" matches any symbol ending with ".trg"
    if pat == "*.trg":
        return sym.endswith(".trg")
    return sym == pat


def _parse_int(x) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def expand_text_trg(core, parts):
    # Expand $sub:key (only keys ending with .trg) to scalar int
    out = []
    changed = False
    for p in parts:
        if isinstance(p, str) and p.startswith("$") and ":" in p:
            sub, key = p[1:].split(":", 1)
            if key.endswith(".trg"):
                try:
                    core._require_kv_sub(TEXTS_ROOT, sub)
                    v = core.kvl[TEXTS_ROOT][sub].get(key, "0")
                except Exception:
                    v = "0"
                out.append(str(_parse_int(v)))
                changed = True
                continue
        out.append(p)
    return out if changed else parts


def expand_table_trg(core, parts):
    # Expand #path (where last segment ends with .trg) leaf scalar to int
    from system.lib import tables as tbl

    out = []
    changed = False
    for p in parts:
        if isinstance(p, str) and p.startswith("#"):
            path = [x for x in p[1:].split(":") if x] if len(p) > 1 else []
            if path and str(path[-1]).endswith(".trg"):
                try:
                    node = tbl.node_get(core.tables, tbl.ROOT, path)
                    if isinstance(node, dict):
                        v = 0
                    else:
                        v = _parse_int("" if node is None else node)
                except Exception:
                    v = 0
                out.append(str(v))
                changed = True
                continue
        out.append(p)
    return out if changed else parts


def _resolve_trg_int(core, sym: str) -> int:
    # Let core._expand try to resolve it via registered expanders.
    # If it doesn't change, treat as 0.
    try:
        parts2 = core._expand([sym])
    except Exception:
        return 0
    if not parts2 or parts2[0] == sym:
        return 0
    return _parse_int(parts2[0])


def _event_worker(core):
    TICK = 0.05  # 50ms
    while not core._event_stop.is_set():
        # watched symbols (dedup, stable)
        symbols = []
        for e in core.events:
            s = e.get("symbol")
            if isinstance(s, str) and s not in symbols:
                symbols.append(s)

        for sym in symbols:
            val = _resolve_trg_int(core, sym)

            # purge-only
            if val == 3:
                core.events = [e for e in core.events if e.get("symbol") != sym]
                core.event_latch.pop(sym, None)
                continue

            latch = core.event_latch.setdefault(sym, {"armed": True})

            if val == 0:
                latch["armed"] = True
                continue

            if not latch.get("armed", True):
                continue

            # fire once per (sym,val), then disarm until back to 0
            latch["armed"] = False

            matches = [e for e in core.events if e.get("symbol") == sym and int(e.get("value", 0)) == val]
            for e in matches:
                cmd_parts = e.get("command", [])
                if not cmd_parts:
                    continue

                # hard rule: events cannot control runners (%)
                if len(cmd_parts) >= 2 and cmd_parts[0] in ("run", "status", "pause", "stop") and str(cmd_parts[1]).startswith("%"):
                    continue

                core.execute(" ".join(str(x) for x in cmd_parts))

        time.sleep(TICK)


def _ensure_event_thread(core):
    if core._event_thread and core._event_thread.is_alive():
        return
    core._event_stop.clear()
    t = threading.Thread(target=_event_worker, args=(core,), name="event:poll", daemon=True)
    core._event_thread = t
    t.start()


def on(core, symbol, value, *command_parts):
    sym = str(symbol)
    if not _is_trg_symbol(sym):
        raise ValueError("ON expects a *.trg symbol")

    v = _parse_int(value)
    if v == 0:
        raise ValueError("ON value cannot be 0")
    if v == 3:
        raise ValueError("ON cannot bind value 3 (3 is purge-only)")

    if not command_parts:
        raise ValueError("ON expects a command")

    # Reject runner control from events
    if len(command_parts) >= 2 and command_parts[0] in ("run", "status", "pause", "stop") and str(command_parts[1]).startswith("%"):
        raise ValueError("Events cannot control runners (%)")

    core.events.append({
        "symbol": sym,
        "value": int(v),
        "command": list(command_parts),
    })

    _ensure_event_thread(core)
    return "OK"


def show(core, pattern):
    pat = str(pattern)
    lines = []
    for e in core.events:
        sym = e.get("symbol", "")
        if _match_pattern(sym, pat):
            lines.append(f'{sym} {int(e.get("value", 0))} ' + " ".join(str(x) for x in e.get("command", [])))
    return "\n".join(lines)


def reset(core, pattern):
    pat = str(pattern)
    removed_syms = set()
    keep = []
    for e in core.events:
        sym = e.get("symbol", "")
        if _match_pattern(sym, pat):
            removed_syms.add(sym)
            continue
        keep.append(e)
    core.events = keep
    for sym in removed_syms:
        core.event_latch.pop(sym, None)
    return "OK"


COMMANDS = {
    "sys.ev.on":    (on,    "Bind an event to a trigger symbol", "sys.ev.on <symbol.trg> <N> <command...>"),
    "sys.ev.show":  (show,  "Show bindings",                     "sys.ev.show <symbol.trg|*.trg>"),
    "sys.ev.reset": (reset, "Remove bindings",                   "sys.ev.reset <symbol.trg|*.trg>"),
}
