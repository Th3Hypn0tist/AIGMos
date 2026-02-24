"""system/core.py

Core runtime + init_core() wiring.

Important: avoid importing system.topics (ALL_COMMANDS) at module import time,
to prevent circular-import issues while building the command surface.
"""

from __future__ import annotations

import json
from pathlib import Path

from system.model.schema import KVL_ROOTS, LIST_ROOTS, TABLES_ROOT

class Core:
    def __init__(self):
        self.kv_roots = set(KVL_ROOTS)
        self.list_roots = set(LIST_ROOTS)

        # Three shapes share the same root/sub concept:
        # - kvlists: root -> sub -> dict[key -> scalar]
        # - lists:   root -> sub -> list[scalar]
        # - tables:  TABLES_ROOT -> infinite dict (tree store for #)
        self.state = {
            "kvlists": {root: {} for root in self.kv_roots},
            "lists": {root: {} for root in self.list_roots},
            "tables": {TABLES_ROOT: {}},
        }

        # convenience aliases (core-owned stores)
        self.kvl = self.state["kvlists"]
        self.l = self.state["lists"]
        self.tables = self.state["tables"]

        self.commands = {}   # cmd -> {handler, help, usage}
        self.log = []
        self.expanders = []
        self.expand_max_passes = 10  # default; can be overridden by config/core.json
        self.alias_mgr = None  # set in init_core()

        # ---- runtime gates ----
        # Serialize core.execute across background threads (runner + events poller)
        import threading
        self.exec_lock = threading.RLock()

        # ---- runner runtime ----
        self.runners = {}        # name -> RunnerJob
        self.runner_locks = {}   # "&name" -> {"runner": "%name", "state": "running|paused"}

        # ---- event runtime ----
        self.events = []         # [{symbol, value, command_parts}]
        self.event_latch = {}    # symbol -> {"armed": bool}
        self._event_thread = None
        self._event_stop = threading.Event()

    def dispatch_internal(self, parts):
        """Dispatch internal sys.* tokens without further expansion."""
        if not parts:
            return ""
        cmd = parts[0]
        entry = self.commands.get(cmd)
        if not entry:
            raise ValueError(f"Unknown command: {cmd}")
        return entry["handler"](self, *parts[1:])

    def register(self, name, handler, help_text="", usage=""):
        self.commands[name] = {"handler": handler, "help": help_text, "usage": usage}

    def add_expander(self, fn):
        self.expanders.append(fn)

    # ---- schema guards (not security) ----
    def _require_kv_root(self, root):
        if root not in self.state["kvlists"]:
            raise ValueError(f"Unknown kv root: {root}")

    def _require_list_root(self, root):
        if root not in self.state["lists"]:
            raise ValueError(f"Unknown list root: {root}")

    def _require_kv_sub(self, root, sub):
        self._require_kv_root(root)
        if sub not in self.state["kvlists"][root]:
            raise ValueError(f"Sub not found: kv/{root}/{sub}")

    def _require_list_sub(self, root, sub):
        self._require_list_root(root)
        if sub not in self.state["lists"][root]:
            raise ValueError(f"Sub not found: list/{root}/{sub}")
    # --------------------------------------

    def _expand(self, parts):
        seen = set()
        for _ in range(self.expand_max_passes):
            sig = tuple(parts)
            if sig in seen:
                raise ValueError("Expansion loop detected")
            seen.add(sig)

            changed = False
            for ex in self.expanders:
                new_parts = ex(parts)
                if new_parts != parts:
                    parts = new_parts
                    changed = True
                    break
            if not changed:
                return parts

        raise ValueError(f"Expansion depth exceeded (max_passes={self.expand_max_passes})")

    def execute(self, raw):
        with self.exec_lock:
            self.log.append({"in": raw})

            parts = raw.strip().split()
            if not parts:
                return None

            # --- EXPOSED SURFACE GATE: only aliases + help ---
            head = parts[0]
            if head != "help":
                if not self.alias_mgr or not self.alias_mgr.has_alias(head):
                    return "Unknown command"
            # ----------------------------------------------

            try:
                parts = self._expand(parts)
            except Exception as e:
                out = f"Error: {e}"
                self.log.append({"out": out})
                return out

            cmd, *args = parts
            entry = self.commands.get(cmd)
            if not entry:
                return f"Unknown command: {cmd}"

            try:
                out = entry["handler"](self, *args)
            except Exception as e:
                out = f"Error: {e}"

            self.log.append({"out": out})
            return out


# ---------- exposed help: only aliases ----------
def help_cmd(core, name=None):
    am = core.alias_mgr
    surface = am.list_aliases() if am else []

    if name:
        exp = am.get_alias(name) if am else None
        if exp is None:
            return "Alias not found"
        return (
            "Command: " + str(name) + "\n"
            "Type:    User-surface alias\n"
            "Note:    Expands internally to sys.* primitive\n"
            "Expands: " + str(exp)
        )

    lines = []
    lines.append("HGI Command Surface")
    lines.append("----------------------------------------")
    lines.append("")
    lines.append("Surface commands:")
    for cmd in surface:
        lines.append("  - " + cmd)
    lines.append("")
    lines.append("Syntax:")
    lines.append("  $sub         Text namespace")
    lines.append("  &name        Routine namespace")
    lines.append("  #path        Table/tree path (#a:b:c) (infinite dict store; leaf via cat, node via ls)")
    lines.append("  $sub:key     Specific text key under texts/<sub>")
    lines.append("  %name        Background runner name (used with run %name ...)")
    lines.append("  *.trg        Numeric trigger bus (events)")
    lines.append("")
    lines.append("Examples:")
    lines.append("  run mk $x")
    lines.append("  run %build &build")
    lines.append("  ON %build.trg 1 Q build_ok")
    lines.append("  ON.show *.trg")
    return "\n".join(lines)


def init_core():
    # Late imports to avoid circular-import issues.
    from system.aliases import AliasManager, ALIASES
    from system.topics import ALL_COMMANDS
    from system.topics.runner import expand_runner_trg
    from system.topics.events import expand_text_trg, expand_table_trg

    core = Core()

    def _load_core_config():
        p = Path("config/core.json")
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    cfg = _load_core_config()
    if "expand_max_passes" in cfg:
        try:
            core.expand_max_passes = int(cfg["expand_max_passes"])
        except Exception:
            pass

    # register internal primitives
    for name, (handler, help_text, usage) in ALL_COMMANDS.items():
        core.register(name, handler, help_text, usage)

    # attach aliases
    core.alias_mgr = AliasManager(ALIASES)
    core.add_expander(core.alias_mgr.expand)

    # *.trg numeric expanders
    core.add_expander(lambda parts: expand_runner_trg(core, parts))
    core.add_expander(lambda parts: expand_text_trg(core, parts))
    core.add_expander(lambda parts: expand_table_trg(core, parts))

    # exposed help
    core.register(
        "help",
        help_cmd,
        "Show available theme commands (aliases)",
        "help [alias]"
    )

    return core
