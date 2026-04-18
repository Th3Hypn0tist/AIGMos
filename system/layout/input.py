from __future__ import annotations

import curses
from typing import Any

from . import keymap as layout_keymap
from . import registry
from .loader import load_module
from .lib import editor as layout_editor
from system.state.api import read_value

_BACKSPACE_KEYS = layout_editor._BACKSPACE_KEYS
_DELETE_KEYS = layout_editor._DELETE_KEYS
_ENTER_KEYS = layout_editor._ENTER_KEYS


def _ui(ctx) -> dict[str, Any]:
    return layout_editor.ui_root(ctx)


def _editor_defaults() -> dict[str, Any]:
    return layout_editor.editor_defaults()


def get_editor(ctx, handle: str | None = None) -> dict[str, Any]:
    return layout_editor.get_editor(ctx, handle)


def get_module_ui(ctx, handle: str) -> dict[str, Any]:
    return layout_editor.get_module_ui(ctx, handle)


def _mark_dirty(ctx, module_handle: str | None = None, *, full: bool = False) -> None:
    return layout_editor.mark_dirty(ctx, module_handle, full=full)


def _insert_text(editor: dict[str, Any], text: str) -> None:
    return layout_editor.insert_text(editor, text)


def _history_commit(editor: dict[str, Any], line: str) -> None:
    return layout_editor.history_commit(editor, line)


def _history_up(editor: dict[str, Any]) -> None:
    return layout_editor.history_up(editor)


def _history_down(editor: dict[str, Any]) -> None:
    return layout_editor.history_down(editor)


def _submit_line(ctx, editor: dict[str, Any]) -> None:
    layout_editor.submit_line(ctx, editor)


def _handle_cs_key(ctx, module_handle: str, key: int | str) -> None:
    layout_editor.handle_key(ctx, module_handle, key)


def _handle_monitor_key(ctx, module_handle: str, key: int) -> None:
    ui = get_module_ui(ctx, module_handle)
    if key == curses.KEY_UP:
        ui["follow"] = False
        ui["scroll"] = max(0, int(ui.get("scroll", 0) or 0) - 1)
        _mark_dirty(ctx, module_handle)
        return
    if key == curses.KEY_DOWN:
        ui["scroll"] = int(ui.get("scroll", 0) or 0) + 1
        _mark_dirty(ctx, module_handle)
        return
    if key == curses.KEY_HOME:
        ui["follow"] = False
        ui["scroll"] = 0
        _mark_dirty(ctx, module_handle)
        return
    if key == curses.KEY_END:
        ui["follow"] = True
        _mark_dirty(ctx, module_handle)
        return



def _handle_list_key(ctx, module_handle: str, key: int) -> None:
    ui = get_module_ui(ctx, module_handle)
    inst = registry.get_instance(ctx, module_handle)
    value = read_value(ctx.get("state"), inst.primary_target, None) if ctx.get("state") is not None else None
    if isinstance(value, dict):
        size = len(value)
    elif isinstance(value, list):
        size = len(value)
    else:
        size = 0
    if size <= 0:
        return
    selected = int(ui.get("selected", 0) or 0)
    if key == curses.KEY_UP:
        ui["selected"] = max(0, selected - 1)
        _mark_dirty(ctx, module_handle)
    elif key == curses.KEY_DOWN:
        ui["selected"] = min(size - 1, selected + 1)
        _mark_dirty(ctx)



def handle_key(ctx, key: int | str) -> None:
    if key == curses.KEY_RESIZE:
        _mark_dirty(ctx, full=True)
        return
    if key in {9, "\t"}:
        registry.cycle_focus(ctx, 1)
        _mark_dirty(ctx, full=True)
        return

    focused = registry.get_focused_module_handle(ctx)
    if not focused:
        return

    inst = registry.get_instance(ctx, focused)
    module = load_module(str(getattr(inst, "MODULE", "") or ""))
    handler = getattr(module, "handle_key", None)
    if callable(handler) and bool(handler(ctx, focused, key)):
        return


def handle_alt_key(ctx, key: int | str) -> None:
    if isinstance(key, str) and len(key) == 1 and key.isdigit():
        slot = 10 if key == "0" else int(key)
    elif isinstance(key, int) and 48 <= key <= 57:
        slot = 10 if key == ord("0") else int(chr(key))
    else:
        return
    bindings = layout_keymap.list_bindings(ctx.get("state"))
    command = str(bindings.get(slot) or "").strip()
    if command:
        registry.dispatch_line(ctx, command)
        _mark_dirty(ctx, full=True)
    return

