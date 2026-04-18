# system/cs/parser.py

from __future__ import annotations

import importlib.util
import shlex
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from system.cs.symbols import is_symbol_line, parse_assignment, parse_runner_control
from system.runtime.runner import runner_control, set_runner_autostart
from system.runtime.runner_store import set_runner_autostart as set_runner_autostart_persistent
from system.runtime.runner_store import set_runner_mode_persistent


@dataclass
class HandlerResponse:
    result: Any = None
    buffer_output: str = ""
    error: str = ""
    force_render: bool = False


@dataclass
class CommandDef:
    command: str
    handler: Callable[..., HandlerResponse]
    help_short: str
    help_full: str


class Parser:
    def __init__(self, state) -> None:
        self.state = state
        self.registry: Dict[str, CommandDef] = {}
        self.runtime: dict[str, Any] = {}
        self.should_exit = False
        self.force_render = False
        self._parse_lock = threading.RLock()
        self._load_commands()

    # ------------------------------------------------------------------
    # command loading
    # ------------------------------------------------------------------

    def _load_commands(self) -> None:
        commands_dir = Path(__file__).resolve().parent / "commands"

        for file_path in sorted(commands_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            module_name = f"system.cs.commands.{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            command = getattr(module, "command", None)
            handler = getattr(module, "handler", None)
            help_short = getattr(module, "help_short", "")
            help_full = getattr(module, "help_full", "")

            if not command or not callable(handler):
                continue

            self.registry[command] = CommandDef(
                command=str(command),
                handler=handler,
                help_short=str(help_short or ""),
                help_full=str(help_full or ""),
            )

    # ------------------------------------------------------------------
    # main parse
    # ------------------------------------------------------------------

    def parse(self, input_line: str) -> Optional[str]:
        with self._parse_lock:
            line = str(input_line or "").strip()
            if not line:
                return None

            if is_symbol_line(line):
                return self._parse_symbol_line(line)

            command_name = "/" if line.startswith("/") else line.split()[0]
            cmd = self.registry.get(command_name)

            if cmd is None and not line.startswith("/") and "." in command_name:
                base_name = command_name.split(".", 1)[0]
                cmd = self.registry.get(base_name)

            if cmd is None:
                return self._handle_error(line, f"unknown command: {command_name}")

            try:
                response = cmd.handler(line, self)
            except Exception as exc:
                return self._handle_error(line, f"handler crash: {exc}")

            if response is None:
                response = HandlerResponse()
            elif isinstance(response, dict):
                response = HandlerResponse(
                    result=response.get("result"),
                    buffer_output=str(response.get("buffer_output") or ""),
                    error=str(response.get("error") or ""),
                    force_render=bool(response.get("force_render", False)),
                )
            elif not isinstance(response, HandlerResponse):
                return self._handle_error(
                    line,
                    f"invalid handler response from {cmd.command}: {type(response).__name__}",
                )

            if response.error:
                return self._handle_error(line, response.error)

            if response.result is not None:
                output_target = self._extract_output_target(line)
                if not output_target:
                    return self._handle_error(line, "missing output target")

                result = self.state.set(output_target, response.result)
                if result["error"]:
                    return self._handle_error(line, result["error"])

            if response.buffer_output:
                self._write_buffer(response.buffer_output)

            if response.force_render:
                self._set_force_render()

            return None

    # ------------------------------------------------------------------
    # symbol handling
    # ------------------------------------------------------------------

    def _parse_symbol_line(self, line: str) -> Optional[str]:
        try:
            runner_cmd = parse_runner_control(line)
            if runner_cmd is not None:
                runner_control(runner_cmd["target"], runner_cmd["token"])

                if runner_cmd["token"] in {"once", "cycle", "loop"}:
                    set_runner_mode_persistent(
                        self.state,
                        runner_cmd["target"],
                        runner_cmd["token"],
                    )

                return None

            if "=" in line:
                assign = parse_assignment(line)

                if assign["target"].startswith("%") and assign["target"].endswith(".autostart"):
                    runner_name = assign["target"].rsplit(".", 1)[0]
                    autostart = set_runner_autostart_persistent(
                        self.state,
                        runner_name,
                        assign["value"],
                    )
                    set_runner_autostart(runner_name, autostart)
                    return None

                result = self.state.set(assign["target"], assign["value"])
                if result["error"]:
                    return self._handle_error(line, result["error"])

                return None

            return self._handle_error(line, f"unsupported symbol syntax: {line}")

        except Exception as exc:
            return self._handle_error(line, f"symbol handler crash: {exc}")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _extract_output_target(self, line: str) -> Optional[str]:
        if line.startswith("/"):
            return None

        try:
            tokens = shlex.split(line)
        except Exception:
            tokens = line.split()

        if len(tokens) < 2:
            return None

        candidate = tokens[1]
        if candidate and candidate[0] in "$#&%@!":
            return candidate

        return None

    def _set_force_render(self) -> None:
        self.force_render = True

        flags = self.runtime.get("flags")
        if isinstance(flags, dict):
            flags["force_render"] = True



    def _write_buffer(self, message: str) -> None:
        if self.runtime.get("buffer_suppress"):
            self._set_force_render()
            return
            
        pushed_live = False

        try:
            ui_thread_id = self.runtime.get("ui_thread_id")
            live_push = self.runtime.get("buffer_live_push")

            if (
                ui_thread_id is not None
                and threading.get_ident() != ui_thread_id
                and callable(live_push)
            ):
                live_push(message)
                pushed_live = True
        except Exception:
            pushed_live = False

        try:
            out = self.state.get("$SYSTEM.BUFFER")
            if out["error"]:
                self._set_force_render()
                return

            current = out["result"] or {}
            if not isinstance(current, dict):
                current = {}

            nums = []
            for key in current.keys():
                try:
                    nums.append(int(key))
                except Exception:
                    pass

            next_key = str((max(nums) if nums else 0) + 1)
            current[next_key] = message

            result = self.state.set("$SYSTEM.BUFFER", current)
            if result["error"]:
                self._set_force_render()
                return

            self._set_force_render()

        except Exception:
            self._set_force_render()
            return

        if pushed_live:
            return

    def _write_error_log(self, full_command: str, errormsg: str) -> None:
        try:
            out = self.state.get("$SYSTEM.ERRORS")
            if out["error"]:
                return

            current = out["result"] or {}
            if not isinstance(current, dict):
                current = {}

            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            key = ts
            while key in current:
                key = str(int(key) + 1)

            current[key] = f"{full_command};{errormsg}"

            result = self.state.set("$SYSTEM.ERRORS", current)
            if result["error"]:
                return

        except Exception:
            return

    def _handle_error(self, full_command: str, errormsg: str) -> str:
        try:
            self._write_error_log(full_command, errormsg)
        except Exception:
            pass

        try:
            self._write_buffer(f"[error] {errormsg}")
        except Exception:
            pass

        return errormsg

    # ------------------------------------------------------------------
    # help api
    # ------------------------------------------------------------------

    def _resolve_help_command(self, name: str) -> Optional[CommandDef]:
        wanted = str(name or "").strip()
        if not wanted:
            return None

        if wanted in self.registry:
            return self.registry[wanted]

        if wanted.startswith("/"):
            return self.registry.get("/")

        if "." in wanted:
            base = wanted.split(".", 1)[0]
            if base in self.registry:
                return self.registry[base]

        return self.registry.get(wanted)

    def get_full_help(self, name: str) -> str:
        cmd = self._resolve_help_command(name)
        if cmd is None:
            return f"[error] unknown command: {name}"

        if cmd.help_full:
            return cmd.help_full

        if cmd.help_short:
            return f"{cmd.command} -> {cmd.help_short}"

        return f"{cmd.command} -> no help available"

    def get_short_help(self, name: Optional[str] = None):
        if name is None:
            return {k: v.help_short for k, v in sorted(self.registry.items())}

        cmd = self._resolve_help_command(name)
        if cmd is None:
            return f"[error] unknown command: {name}"

        if cmd.help_short:
            return f"{cmd.command} -> {cmd.help_short}"

        if cmd.help_full:
            first = cmd.help_full.strip().splitlines()[0].strip()
            if first:
                return first

        return f"{cmd.command} -> no help available"

    def get_help_index(self) -> list[str]:
        lines: list[str] = []

        for key, cmd in sorted(self.registry.items()):
            if key != cmd.command:
                continue
            if cmd.command == "/":
                continue

            if cmd.help_short:
                lines.append(f"{cmd.command} -> {cmd.help_short}")
            elif cmd.help_full:
                first = cmd.help_full.strip().splitlines()[0].strip()
                if first:
                    lines.append(first)
                else:
                    lines.append(f"{cmd.command} -> no help available")
            else:
                lines.append(f"{cmd.command} -> no help available")

        return lines
