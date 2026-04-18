# system/cs/parser.py
from __future__ import annotations

import shlex
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from system.cs.command_registry import (
    get_full_help as registry_get_full_help,
    get_help_index as registry_get_help_index,
    get_short_help as registry_get_short_help,
    load_commands,
    resolve_command,
)
from system.cs.models import CommandDef, HandlerResponse
from system.cs.reporter import handle_error, write_buffer
from system.cs.resolver import maybe_expand_direct_exec_symbol
from system.cs.runtime_ctx import force_render
from system.cs.symbol_handler import parse_symbol_line
from system.cs.symbols import is_symbol_line
from system.state.api import write_value


def _parser_writer_tag(command_name: str) -> str:
    clean = str(command_name or "").strip()
    return f"parser:{clean}" if clean else "parser:unknown"


def _maybe_handle_layout_instance_switch(parser, line: str) -> Optional[str]:
    clean = str(line or "").strip()
    if not clean or not clean.startswith("|"):
        return None
    if any(ch.isspace() for ch in clean) or "=" in clean:
        return None

    ctx = parser.runtime.get("ctx")
    if not isinstance(ctx, dict):
        return handle_error(parser, clean, "layout runtime context missing")

    try:
        from system.layout import registry as layout_registry

        target = layout_registry.ensure_instance(ctx, clean)
        handle = str(getattr(target, "handle", target) or clean).strip() or clean
        layout_registry.switch_active(ctx, handle)
        force_render(parser)
        return None
    except Exception as exc:
        return handle_error(parser, clean, str(exc))


class Parser:
    def __init__(self, state) -> None:
        self.state = state
        self.registry: Dict[str, CommandDef] = {}
        self.runtime: dict[str, Any] = {}
        self.should_exit = False
        self.force_render = False
        self._parse_lock = threading.RLock()
        self._load_commands()

    def _load_commands(self) -> None:
        commands_dir = Path(__file__).resolve().parent / "commands"
        self.registry = load_commands(commands_dir)

    def parse(self, input_line: str) -> Optional[str]:
        with self._parse_lock:
            line = str(input_line or "").strip()
            if not line:
                return None

            command_name = "/" if line.startswith("/") else line.split()[0]
            writer_tag = _parser_writer_tag(command_name)
            previous_writer_tag = self.runtime.get("_active_writer_tag")
            previous_ext = self.runtime.get("_active_command_is_extension")
            previous_pkg = self.runtime.get("_active_command_source_package")

            self.runtime["_active_writer_tag"] = writer_tag
            self.runtime["_active_command_is_extension"] = False
            self.runtime["_active_command_source_package"] = ""
            try:
                if "=" not in line:
                    try:
                        expanded = maybe_expand_direct_exec_symbol(self, line)
                    except Exception as exc:
                        return handle_error(self, line, str(exc))

                    if expanded != line:
                        return self.parse(expanded)

                layout_switch_result = _maybe_handle_layout_instance_switch(self, line)
                if layout_switch_result is not None:
                    return layout_switch_result
                if line.startswith("|") and "=" not in line and not any(ch.isspace() for ch in line):
                    return None

                if is_symbol_line(line):
                    return parse_symbol_line(self, line)

                cmd = resolve_command(self.registry, line)
                if cmd is None:
                    return handle_error(self, line, f"unknown command: {command_name}")

                writer_tag = _parser_writer_tag(cmd.command)
                self.runtime["_active_writer_tag"] = writer_tag
                self.runtime["_active_command_is_extension"] = bool(getattr(cmd, "is_extension", False))
                self.runtime["_active_command_source_package"] = str(getattr(cmd, "source_package", "") or "")

                try:
                    response = cmd.handler(line, self)
                except Exception as exc:
                    return handle_error(self, line, f"handler crash: {exc}")

                if response is None:
                    response = HandlerResponse()
                elif not isinstance(response, HandlerResponse):
                    return handle_error(self, line, f"invalid handler response from {cmd.command}: {type(response).__name__}")

                if response.error:
                    return handle_error(self, line, response.error)

                if response.result is not None:
                    output_target = self._extract_output_target(line)
                    if not output_target:
                        return handle_error(self, line, "missing output target")

                    result = write_value(
                        self.state,
                        output_target,
                        response.result,
                        writer=writer_tag,
                        op="command_result",
                    )
                    if result["error"]:
                        return handle_error(self, line, result["error"])

                if response.buffer_output:
                    write_buffer(self, response.buffer_output)

                if response.force_render:
                    force_render(self)

                return None
            finally:
                if previous_writer_tag is None:
                    self.runtime.pop("_active_writer_tag", None)
                else:
                    self.runtime["_active_writer_tag"] = previous_writer_tag
                if previous_ext is None:
                    self.runtime.pop("_active_command_is_extension", None)
                else:
                    self.runtime["_active_command_is_extension"] = previous_ext
                if previous_pkg is None:
                    self.runtime.pop("_active_command_source_package", None)
                else:
                    self.runtime["_active_command_source_package"] = previous_pkg

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
        if candidate and candidate[0] in "$#&%@!|":
            return candidate

        return None

    def get_full_help(self, name: str) -> str:
        return registry_get_full_help(self.registry, name)

    def get_short_help(self, name: Optional[str] = None):
        return registry_get_short_help(self.registry, name)

    def get_help_index(self) -> list[str]:
        return registry_get_help_index(self.registry)
