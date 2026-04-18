from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import Callable


GREETING_TEXT = """


   #    ###  #####  #     #
  # #    #  #     # ##   ##  ####   ####
 #   #   #  #       # # # # #    # #
#     #  #  #  #### #  #  # #    #  ####     
#######  #  #     # #     # #    #      #
#     #  #  #     # #     # #    # #    #
#     # ###  #####  #     #  ####   ####      

      The HGI Command Surface
      
      
"""

_boot_lock = threading.RLock()
_boot_flags_ref: dict | None = None


def _terminal_clear() -> None:
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "cls"], check=False)
        return

    clear_cmd = shutil.which("clear")
    if clear_cmd:
        subprocess.run([clear_cmd], check=False)
        return

    print("\033[2J\033[H", end="", flush=True)


def bind_boot_flags(flags: dict | None) -> None:
    global _boot_flags_ref
    with _boot_lock:
        _boot_flags_ref = flags if isinstance(flags, dict) else None


def _flags() -> dict | None:
    with _boot_lock:
        return _boot_flags_ref


def boot_log(message: str) -> None:
    text = str(message or '').rstrip('\n')
    if not text:
        return
    flags = _flags()
    if isinstance(flags, dict):
        lines = flags.setdefault('boot_log_lines', [])
        if isinstance(lines, list):
            lines.append(text)
            flags['force_render'] = True
            return
    print(text, flush=True)


def boot_terminal_clear(state, flags) -> None:
    _ = state
    flags['boot_screen_clear'] = True


def boot_greeting(state, flags) -> None:
    _ = state
    flags['boot_greeting_text'] = GREETING_TEXT
    flags['boot_splash_active'] = True
    flags['boot_wait_for_key'] = False
    flags['boot_startup_started'] = False
    flags['boot_startup_done'] = False
    flags.setdefault('boot_log_lines', [])


BOOT_HOOKS: tuple[Callable[..., None], ...] = (
    boot_terminal_clear,
    boot_greeting,
)


def run_boot_hooks(state, flags) -> None:
    _ = state
    bind_boot_flags(flags)
    for hook in BOOT_HOOKS:
        hook(state, flags)
