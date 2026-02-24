# lobster_tui.py
import readline
from system.core import init_core

def main():
    core = init_core()
    print("Stage0 REPL (dict -> dict -> dict + expander pipeline)")
    print("Commands: help (lists aliases).")
    print("Exit: quit/exit\n")

    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip() in ("quit", "exit"):
            break
        res = core.execute(line)
        if res is not None:
            print(res)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
