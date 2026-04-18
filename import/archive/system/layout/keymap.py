from __future__ import annotations

from typing import Callable

from prompt_toolkit.key_binding import KeyBindings


SLOT_ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
COMMAND_PREFIX = "__AIGMOS_COMMAND__:"


def normalize_slot(token: str) -> str:
    raw = str(token or "").strip().lower()
    if raw.startswith("alt-"):
        raw = raw[4:]
    if raw.startswith("alt") and len(raw) == 4 and raw[-1] in SLOT_ORDER:
        raw = raw[-1]
    if raw not in SLOT_ORDER:
        raise ValueError("slot must be alt-1..alt-9 or alt-0")
    return raw


def slot_label(slot: str) -> str:
    return f"alt-{normalize_slot(slot)}"


def state_symbol(slot: str) -> str:
    return f"#SYSTEM:keymap:alt:{normalize_slot(slot)}"


def get_binding(state, slot: str) -> str:
    out = state.get(state_symbol(slot))
    if out["error"]:
        return ""
    value = out["result"]
    if value is None:
        return ""
    return str(value).strip()


def set_binding(state, slot: str, command: str) -> None:
    clean_slot = normalize_slot(slot)
    clean_command = str(command or "").strip()
    if not clean_command:
        raise ValueError("binding command cannot be empty")
    out = state.set(state_symbol(clean_slot), clean_command)
    if out["error"]:
        raise RuntimeError(out["error"])


def clear_binding(state, slot: str) -> None:
    clean_slot = normalize_slot(slot)
    out = state.delete(state_symbol(clean_slot))
    if out["error"]:
        raise RuntimeError(out["error"])


def list_bindings(state) -> dict[str, str]:
    out: dict[str, str] = {}
    for slot in SLOT_ORDER:
        value = get_binding(state, slot)
        if value:
            out[slot] = value
    return out


def _dispatch_bound_command(resolve_command: Callable[[str], str], slot: str) -> str:
    command = str(resolve_command(slot) or "").strip()
    if not command:
        command = f"echo [unbound] {slot_label(slot)}"
    return COMMAND_PREFIX + command


def build_key_bindings(resolve_command: Callable[[str], str]) -> KeyBindings:
    kb = KeyBindings()

    def _bind(slot: str) -> None:
        @kb.add("escape", slot)
        def _handler(event) -> None:
            event.app.exit(result=_dispatch_bound_command(resolve_command, slot))

    for slot in SLOT_ORDER:
        _bind(slot)

    return kb
