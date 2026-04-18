from __future__ import annotations

from system.cs.lib.qcall import set_active_profile


DEFAULT_LAYOUT = "buffer"


def force_render(ctx) -> None:
    parser = ctx["parser"]
    parser.force_render = True
    flags = parser.runtime.get("flags")
    if isinstance(flags, dict):
        flags["force_render"] = True


def set_layout(ctx, name: str) -> bool:
    out = ctx["state"].set("$SYSTEM.LAYOUT", str(name or DEFAULT_LAYOUT).strip().lower() or DEFAULT_LAYOUT)
    if out["error"]:
        return False
    force_render(ctx)
    return True


def _resolve_q_alias(token: str) -> str:
    raw = str(token or "").strip().lower()
    if "." not in raw:
        return "default"
    return raw.split(".", 1)[1].strip() or "default"


def handle_immediate_ui_command(ctx, line: str) -> bool:
    raw = str(line or "").strip()
    if not raw.startswith("/"):
        return False

    parts = raw.split()
    if not parts:
        return False

    token = parts[0].lower()
    parser = ctx["parser"]

    if token in ("/quit", "/exit") and len(parts) == 1:
        flags = parser.runtime.get("flags")
        if isinstance(flags, dict):
            flags["running"] = False
            flags["force_render"] = True
        return True

    if token == "/buffer" and len(parts) == 1:
        return set_layout(ctx, "buffer")

    if (token == "/q" or token.startswith("/q.")) and len(parts) == 1:
        try:
            set_active_profile(parser, _resolve_q_alias(token))
        except Exception:
            return False
        return set_layout(ctx, "q")

    return False
