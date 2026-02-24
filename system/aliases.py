# system/aliases.py
#
# Stage1: User never invokes sys.* directly.
# Alias expansion is token0 replacement to internal sys.* primitives.

ALIASES = {
    "mk":       "sys.mk",
    "rm":       "sys.rm",
    "ls":       "sys.ls",
    "add.item": "sys.add.item",
    "cat":      "sys.cat",
    "cp":       "sys.cp",
    "mv":       "sys.mv",

    # IO (filesystem boundary)
    "import.file": "sys.io.import.file",
    "import.many": "sys.io.import.many",
    "export.file": "sys.io.export.file",
    "export.many": "sys.io.export.many",

    # Planner (sharding only)
    # "plan":      "sys.plan",
    #"plan.show": "sys.plan.show",
    #"plan.rm":   "sys.plan.rm",

    # run modes:
    #   run <cmd...>                 (single-shot, blocking, NO trigger)
    #   run %name <target|cmd...>    (background runner, HAS %name.trg)
    "run":      "sys.run",
    "status":   "sys.status",
    "pause":    "sys.pause",
    "stop":     "sys.stop",

    # events
    "ON":       "sys.ev.on",
    "ON.show":  "sys.ev.show",
    "ON.reset": "sys.ev.reset",

    # LLM chat (system module)
    "Q":        "sys.q.chat",
}


class AliasManager:
    def __init__(self, aliases):
        self.aliases = dict(aliases)

    def has_alias(self, name: str) -> bool:
        return name in self.aliases

    def expand(self, parts):
        if not parts:
            return parts
        head = parts[0]
        exp = self.aliases.get(head)
        if not exp:
            return parts
        return exp.strip().split() + parts[1:]

    def list_aliases(self):
        return sorted(self.aliases.keys())

    def get_alias(self, name):
        return self.aliases.get(name)
