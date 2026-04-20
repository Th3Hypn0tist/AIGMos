from __future__ import annotations

import curses
from typing import Any


def viewport_tail(lines: list[str], height: int, scroll: int = 0) -> list[str]:
    if not lines:
        return ['']
    height = max(1, int(height or 1))
    max_scroll = max(0, len(lines) - height)
    scroll = max(0, min(int(scroll or 0), max_scroll))
    end = max(0, len(lines) - scroll)
    start = max(0, end - height)
    visible = lines[start:end]
    return visible or ['']


def viewport_head(lines: list[str], height: int, scroll: int = 0) -> list[str]:
    if not lines:
        return ['']
    height = max(1, int(height or 1))
    max_scroll = max(0, len(lines) - height)
    scroll = max(0, min(int(scroll or 0), max_scroll))
    start = min(scroll, max_scroll)
    end = start + height
    visible = lines[start:end]
    return visible or ['']


def normalize_follow_scroll(ui: dict[str, Any]) -> tuple[bool, int]:
    follow = bool(ui.get('follow', True))
    scroll = max(0, int(ui.get('scroll', 0) or 0))
    ui['follow'] = follow
    ui['scroll'] = scroll
    return follow, scroll


def handle_scroll_key(ui: dict[str, Any], key: int, *, kind: str = 'q') -> bool:
    follow, scroll = normalize_follow_scroll(ui)

    if kind == 'monitor':
        if key == curses.KEY_UP:
            ui['follow'] = False
            ui['scroll'] = max(0, scroll - 1)
            return True
        if key == curses.KEY_DOWN:
            ui['scroll'] = scroll + 1
            return True
        if key == curses.KEY_HOME:
            ui['follow'] = False
            ui['scroll'] = 0
            return True
        if key == curses.KEY_END:
            ui['follow'] = True
            return True
        return False

    # q / qmon tail-follow semantics
    if key == curses.KEY_UP:
        ui['follow'] = False
        ui['scroll'] = scroll + 1
        return True
    if key == curses.KEY_DOWN:
        current = max(0, scroll - 1)
        ui['scroll'] = current
        if current == 0:
            ui['follow'] = True
        return True
    if key == curses.KEY_HOME:
        ui['follow'] = False
        ui['scroll'] = 10 ** 9
        return True
    if key == curses.KEY_END:
        ui['follow'] = True
        ui['scroll'] = 0
        return True
    return False
