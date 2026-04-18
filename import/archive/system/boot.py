# system/boot.py

from __future__ import annotations

import os
import shutil
import subprocess
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


def _terminal_clear() -> None:
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "cls"], check=False)
        return

    clear_cmd = shutil.which("clear")
    if clear_cmd:
        subprocess.run([clear_cmd], check=False)
        return

    print("\033[2J\033[H", end="", flush=True)


def boot_terminal_clear(state, flags) -> None:
    _terminal_clear()


def boot_greeting(state, flags) -> None:
    print(GREETING_TEXT, end="", flush=True)


BOOT_HOOKS: tuple[Callable[..., None], ...] = (
    boot_terminal_clear,
    boot_greeting,
)


def run_boot_hooks(state, flags) -> None:
    for hook in BOOT_HOOKS:
        hook(state, flags)
