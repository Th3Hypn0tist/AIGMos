from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict, Optional

from system.cs.command_def import CommandDef
from system.extensions import ensure_extensions_tree, iter_package_module_names, reload_package_modules


_COMMAND_PACKAGES = (
    "system.cs.commands",
    "extensions.commands",
)


def _module_to_command_def(module, package_name: str) -> CommandDef:
    factory = getattr(module, "register", None)
    if not callable(factory):
        raise TypeError(f"{module.__name__} must export register()")
    item = factory()
    if not isinstance(item, CommandDef):
        raise TypeError(f"{module.__name__}.register() must return CommandDef")
    setattr(item, "source_package", package_name)
    setattr(item, "is_extension", package_name.startswith("extensions."))
    return item


def load_commands(_commands_dir: Path | None = None) -> Dict[str, CommandDef]:
    ensure_extensions_tree()
    registry: Dict[str, CommandDef] = {}

    for package_name in _COMMAND_PACKAGES:
        for stem in iter_package_module_names(package_name):
            module = importlib.import_module(f"{package_name}.{stem}")
            item = _module_to_command_def(module, package_name)
            registry[str(item.command)] = item

    return registry


def resolve_command(registry: Dict[str, CommandDef], line: str) -> Optional[CommandDef]:
    command_name = "/" if line.startswith("/") else line.split()[0]
    cmd = registry.get(command_name)

    if cmd is None and not line.startswith("/") and "." in command_name:
        base_name = command_name.split(".", 1)[0]
        cmd = registry.get(base_name)

    return cmd


def resolve_help_command(registry: Dict[str, CommandDef], name: str) -> Optional[CommandDef]:
    wanted = str(name or "").strip()
    if not wanted:
        return None

    if wanted in registry:
        return registry[wanted]

    if wanted.startswith("/"):
        return registry.get("/")

    if "." in wanted:
        base = wanted.split(".", 1)[0]
        if base in registry:
            return registry[base]

    return registry.get(wanted)


def get_full_help(registry: Dict[str, CommandDef], name: str) -> str:
    cmd = resolve_help_command(registry, name)
    if cmd is None:
        return f"[error] unknown command: {name}"

    if cmd.help_full:
        return cmd.help_full

    if cmd.help_short:
        return f"{cmd.command} -> {cmd.help_short}"

    return f"{cmd.command} -> no help available"


def get_short_help(registry: Dict[str, CommandDef], name: Optional[str] = None):
    if name is None:
        return {k: v.help_short for k, v in sorted(registry.items())}

    cmd = resolve_help_command(registry, name)
    if cmd is None:
        return f"[error] unknown command: {name}"

    if cmd.help_short:
        return f"{cmd.command} -> {cmd.help_short}"

    if cmd.help_full:
        first = cmd.help_full.strip().splitlines()[0].strip()
        if first:
            return first

    return f"{cmd.command} -> no help available"


def get_help_index(registry: Dict[str, CommandDef]) -> list[str]:
    lines: list[str] = []

    for key, cmd in sorted(registry.items()):
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



def reload_commands(_commands_dir: Path | None = None) -> Dict[str, CommandDef]:
    reload_package_modules(*_COMMAND_PACKAGES)
    return load_commands(_commands_dir)
