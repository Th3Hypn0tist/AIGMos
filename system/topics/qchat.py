# system/topics/qchat.py
#
# Internal sys.* primitive for LLM chat.
# User reaches this only via alias: Q -> sys.q.chat
#
# Returns ONLY assistant text (no metadata).

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from system.modules.q import QChat


def _project_root() -> Path:
    # .../system/topics/qchat.py -> project root = parents[2]
    return Path(__file__).resolve().parents[2]


_Q_SINGLETON: QChat | None = None


def _get_q() -> QChat:
    global _Q_SINGLETON
    if _Q_SINGLETON is None:
        cfg = _project_root() / "config/llm/default.json"
        if not cfg.exists():
            raise ValueError(f"Q config missing: {cfg}")
        _Q_SINGLETON = QChat(cfg)
    return _Q_SINGLETON



def _expand_q_symbols(core, parts: List[str]) -> str:
    """Expand $sub:key, &name, #path tokens into their resolved text via sys.cat."""
    out_parts: List[str] = []
    for tok in parts:
        if tok.startswith(("$", "&", "#")):
            # Only expand symbol tokens; other words pass through.
            try:
                val = core.dispatch_internal(["sys.cat", tok])
            except Exception as e:
                raise ValueError(f"Q symbol expansion failed for {tok}: {e}")
            out_parts.append(str(val))
        else:
            out_parts.append(tok)
    return " ".join(out_parts).strip()


def q_chat(core, *text_parts: str) -> str:
    """sys.q.chat <text...> -> assistant_text"""
    prompt = _expand_q_symbols(core, list(text_parts))
    if not prompt:
        return ""  # keep feed clean

    q = _get_q()
    messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]

    # Stage0/Stage1 are synchronous; bridge to async.
    try:
        return asyncio.run(q.chat(messages))
    except Exception as e:
        # Surface config context to make debugging 1-shot.
        cfg = getattr(q, "cfg", None)
        if cfg is not None:
            raise ValueError(
                f"Q failed (base_url={cfg.base_url}, model={cfg.model}, timeout_ms={cfg.timeout_ms}) :: {e}"
            ) from e
        raise



COMMANDS = {
    "sys.q.chat": (
        q_chat,
        "LLM chat (returns only assistant text)",
        "sys.q.chat <text...>",
    ),
}