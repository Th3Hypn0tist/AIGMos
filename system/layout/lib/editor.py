from __future__ import annotations

import curses
from typing import Any

_BACKSPACE_KEYS = {curses.KEY_BACKSPACE, 127, 8}
_DELETE_KEYS = {curses.KEY_DC}
_ENTER_KEYS = {10, 13, '\n', '\r', curses.KEY_ENTER}


def ui_root(ctx) -> dict[str, Any]:
    ui = ctx.setdefault('layout_ui', {}) if isinstance(ctx, dict) else {}
    ui.setdefault('editors', {})
    ui.setdefault('modules', {})
    return ui


def editor_defaults() -> dict[str, Any]:
    return {
        'buffer': '',
        'cursor': 0,
        'history': [],
        'history_index': None,
    }


def get_editor(ctx, handle: str | None = None) -> dict[str, Any]:
    from .. import registry

    registry.bootstrap(ctx)
    active = handle or registry.get_focused_module_handle(ctx) or registry.get_active_handle(ctx)
    editors = ui_root(ctx).setdefault('editors', {})
    return editors.setdefault(active, editor_defaults())


def get_module_ui(ctx, handle: str) -> dict[str, Any]:
    from .. import registry

    registry.bootstrap(ctx)
    modules = ui_root(ctx).setdefault('modules', {})
    return modules.setdefault(str(handle or ''), {})


def mark_dirty(ctx, module_handle: str | None = None, *, full: bool = False) -> None:
    from .. import registry

    flags = ctx.setdefault('flags', {}) if isinstance(ctx, dict) else {}
    flags['force_render'] = True
    if full:
        flags['layout_hard_redraw'] = True
        return
    target = str(module_handle or '').strip()
    if not target:
        try:
            target = registry.get_focused_module_handle(ctx) or registry.get_active_handle(ctx)
        except Exception:
            target = ''
    if target:
        dirty = flags.setdefault('layout_dirty_modules', set())
        dirty.add(target)


def insert_text(editor: dict[str, Any], text: str) -> None:
    cursor = int(editor.get('cursor', 0) or 0)
    buf = str(editor.get('buffer', '') or '')
    editor['buffer'] = buf[:cursor] + text + buf[cursor:]
    editor['cursor'] = cursor + len(text)


def history_commit(editor: dict[str, Any], line: str) -> None:
    text = str(line or '')
    if not text.strip():
        editor['history_index'] = None
        return
    history = editor.setdefault('history', [])
    if not history or history[-1] != text:
        history.append(text)
    editor['history_index'] = None


def history_up(editor: dict[str, Any]) -> None:
    history = editor.setdefault('history', [])
    if not history:
        return
    index = editor.get('history_index')
    if index is None:
        index = len(history) - 1
    else:
        index = max(0, int(index) - 1)
    editor['history_index'] = index
    editor['buffer'] = str(history[index])
    editor['cursor'] = len(editor['buffer'])


def history_down(editor: dict[str, Any]) -> None:
    history = editor.setdefault('history', [])
    index = editor.get('history_index')
    if not history or index is None:
        return
    index = int(index)
    if index >= len(history) - 1:
        editor['history_index'] = None
        editor['buffer'] = ''
    else:
        index += 1
        editor['history_index'] = index
        editor['buffer'] = str(history[index])
    editor['cursor'] = len(str(editor.get('buffer', '') or ''))


def clear_editor(ctx, module_handle: str) -> bool:
    editor = get_editor(ctx, module_handle)
    editor['buffer'] = ''
    editor['cursor'] = 0
    editor['history_index'] = None
    return True


def submit_line(ctx, editor: dict[str, Any], *, source_handle: str | None = None, target_handle: str | None = None) -> dict[str, str]:
    from .. import registry

    line = str(editor.get('buffer', '') or '')
    editor['buffer'] = ''
    editor['cursor'] = 0
    if registry.is_ui_instance_switch_line(line):
        editor['history_index'] = None
    else:
        history_commit(editor, line)
    if not line.strip():
        mark_dirty(ctx, full=True)
        return {'mode': 'none'}
    result = registry.dispatch_line(ctx, line, source_handle=source_handle, target_handle=target_handle)
    mark_dirty(ctx, full=True)
    return result


def handle_key(ctx, module_handle: str, key: int | str, *, source_handle: str | None = None, target_handle: str | None = None) -> bool:
    editor = get_editor(ctx, module_handle)
    buf = str(editor.get('buffer', '') or '')
    cursor = int(editor.get('cursor', 0) or 0)

    if key in _ENTER_KEYS:
        submit_line(ctx, editor, source_handle=source_handle, target_handle=target_handle)
        return True
    if key in _BACKSPACE_KEYS:
        if cursor > 0:
            editor['buffer'] = buf[: cursor - 1] + buf[cursor:]
            editor['cursor'] = cursor - 1
            editor['history_index'] = None
            mark_dirty(ctx, module_handle)
        return True
    if key in _DELETE_KEYS:
        if cursor < len(buf):
            editor['buffer'] = buf[:cursor] + buf[cursor + 1 :]
            editor['history_index'] = None
            mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_LEFT:
        editor['cursor'] = max(0, cursor - 1)
        mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_RIGHT:
        editor['cursor'] = min(len(buf), cursor + 1)
        mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_HOME:
        editor['cursor'] = 0
        mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_END:
        editor['cursor'] = len(buf)
        mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_UP:
        history_up(editor)
        mark_dirty(ctx, module_handle)
        return True
    if key == curses.KEY_DOWN:
        history_down(editor)
        mark_dirty(ctx, module_handle)
        return True
    if isinstance(key, str) and key and key not in {'\t', '\n', '\r', '\x1b'}:
        insert_text(editor, key)
        editor['history_index'] = None
        mark_dirty(ctx, module_handle)
        return True
    if isinstance(key, int) and 32 <= key <= 126:
        insert_text(editor, chr(key))
        editor['history_index'] = None
        mark_dirty(ctx, module_handle)
        return True
    return False
