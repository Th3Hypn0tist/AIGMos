from __future__ import annotations

from system.state.api import delete_value, list_symbols, read_value, write_value

SLOT_ORDER = tuple(range(1, 11))


def normalize_slot(raw: str) -> int:
    text = str(raw or "").strip().lower()
    if text.startswith("alt-"):
        text = text[4:]
    if text not in {str(i) for i in range(10)}:
        raise ValueError("slot must be alt-1..alt-9 or alt-0")
    return 10 if text == "0" else int(text)


def slot_label(slot: int) -> str:
    number = int(slot)
    return f"alt-{0 if number == 10 else number}"


def _symbol(slot: int) -> str:
    return f"#SYSTEM:keymap:alt:{0 if int(slot) == 10 else int(slot)}"


def set_binding(state, slot: int, command_text: str) -> None:
    out = write_value(state, _symbol(slot), str(command_text or ""), writer="layout:keymap", op="bind")
    if out.get("error"):
        raise ValueError(str(out["error"]))


def clear_binding(state, slot: int) -> None:
    out = delete_value(state, _symbol(slot), writer="layout:keymap", op="unbind")
    if out.get("error"):
        raise ValueError(str(out["error"]))


def list_bindings(state) -> dict[int, str]:
    out: dict[int, str] = {}
    for slot in SLOT_ORDER:
        value = read_value(state, _symbol(slot), None)
        if value not in (None, ""):
            out[int(slot)] = str(value)
    return out


def dispatch_key(parser_or_ctx, slot: int | str):
    normalized = normalize_slot(str(slot or ""))
    parser = getattr(parser_or_ctx, "parse", None)
    state = getattr(parser_or_ctx, "state", None)
    if parser is None and isinstance(parser_or_ctx, dict):
        parser = parser_or_ctx.get("parser")
        state = parser_or_ctx.get("state")
    value = read_value(state, _symbol(normalized), "")
    text = str(value or "").strip()
    if not text or parser is None:
        return False
    result = parser.parse(text)
    return result is None
