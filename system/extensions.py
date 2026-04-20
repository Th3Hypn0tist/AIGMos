from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS_ROOT = PROJECT_ROOT / "extensions"
SYSTEM_LAYOUT_TEMPLATES_ROOT = PROJECT_ROOT / "system" / "library" / "layout"
EXT_LAYOUT_TEMPLATES_ROOT = EXTENSIONS_ROOT / "layout"
SYSTEM_LAYOUT_MODULES_ROOT = PROJECT_ROOT / "system" / "layout" / "modules"
EXT_LAYOUT_MODULES_ROOT = EXT_LAYOUT_TEMPLATES_ROOT / "modules"
LAYOUT_DEFINITIONS_ROOT = SYSTEM_LAYOUT_TEMPLATES_ROOT
COMMANDS_ROOT = EXTENSIONS_ROOT / "commands"
LAYOUT_ROOT = EXTENSIONS_ROOT / "layout"
ADAPTERS_ROOT = EXTENSIONS_ROOT / "adapters"
INPUTS_ROOT = EXTENSIONS_ROOT / "inputs"

FORBIDDEN_EXTENSION_SYMBOL_PREFIXES = ("$SYSTEM", "#SYSTEM")
FORBIDDEN_EXTENSION_FILES = ("config.json",)


def ensure_extensions_tree() -> None:
    for path in (SYSTEM_LAYOUT_TEMPLATES_ROOT, SYSTEM_LAYOUT_MODULES_ROOT, EXT_LAYOUT_TEMPLATES_ROOT, EXT_LAYOUT_MODULES_ROOT, EXTENSIONS_ROOT, COMMANDS_ROOT, LAYOUT_ROOT, ADAPTERS_ROOT, INPUTS_ROOT):
        path.mkdir(parents=True, exist_ok=True)
        if path not in (SYSTEM_LAYOUT_TEMPLATES_ROOT, SYSTEM_LAYOUT_MODULES_ROOT, EXT_LAYOUT_TEMPLATES_ROOT, EXT_LAYOUT_MODULES_ROOT):
            init_py = path / "__init__.py"
            if not init_py.exists():
                init_py.write_text("", encoding="utf-8")


def import_optional_package(package_name: str):
    try:
        return importlib.import_module(package_name)
    except ModuleNotFoundError:
        return None


def iter_package_module_names(package_name: str) -> list[str]:
    package = import_optional_package(package_name)
    if package is None or not hasattr(package, "__path__"):
        return []

    names = [
        item.name
        for item in pkgutil.iter_modules(package.__path__)
        if not item.name.startswith("_")
    ]
    return sorted(set(names))


def invalidate_import_caches() -> None:
    importlib.invalidate_caches()


def reload_package_modules(*package_names: str) -> list[str]:
    invalidate_import_caches()
    reloaded: list[str] = []

    for package_name in package_names:
        clean = str(package_name or '').strip()
        if not clean:
            continue

        package = import_optional_package(clean)
        if package is not None:
            importlib.reload(package)
            reloaded.append(clean)

        prefix = clean + '.'
        module_names = sorted(
            [name for name in sys.modules.keys() if name.startswith(prefix)],
            key=lambda name: (name.count('.'), name),
        )

        for module_name in module_names:
            module = sys.modules.get(module_name)
            if module is None:
                continue
            importlib.reload(module)
            reloaded.append(module_name)

    return reloaded


def extension_symbol_access_allowed(symbol: str) -> bool:
    raw = str(symbol or "").strip()
    if not raw:
        return False
    return not any(raw.startswith(prefix) for prefix in FORBIDDEN_EXTENSION_SYMBOL_PREFIXES)

def extension_symbol_error(symbol: str, action: str) -> str:
    clean_symbol = str(symbol or "").strip()
    clean_action = str(action or "access").strip() or "access"
    return f"forbidden extension symbol {clean_action}: {clean_symbol}"


def assert_extension_symbol_read_allowed(state, symbol: str) -> None:
    if active_command_is_extension(state) and not extension_symbol_access_allowed(symbol):
        raise PermissionError(extension_symbol_error(symbol, "read"))


def assert_extension_symbol_write_allowed(state, symbol: str) -> None:
    if active_command_is_extension(state) and not extension_symbol_access_allowed(symbol):
        raise PermissionError(extension_symbol_error(symbol, "write"))



def extension_read_path_allowed(path: str) -> bool:
    try:
        candidate = Path(path).expanduser().resolve()
    except Exception:
        return False

    for name in FORBIDDEN_EXTENSION_FILES:
        if candidate.name == name:
            return False

    system_root = (PROJECT_ROOT / "system").resolve()
    if candidate == system_root or system_root in candidate.parents:
        return False

    return True


def extension_write_path_allowed(path: str) -> bool:
    try:
        candidate = Path(path).expanduser().resolve()
    except Exception:
        return False

    system_root = (PROJECT_ROOT / "system").resolve()
    if candidate == system_root or system_root in candidate.parents:
        return False

    for name in FORBIDDEN_EXTENSION_FILES:
        if candidate.name == name:
            return False
    return True


def _state_runtime(state):
    runtime = getattr(state, "_aigmos_runtime", None)
    return runtime if isinstance(runtime, dict) else {}


def active_command_is_extension(state) -> bool:
    runtime = _state_runtime(state)
    return bool(runtime.get("_active_command_is_extension"))


def active_command_source_package(state) -> str:
    runtime = _state_runtime(state)
    return str(runtime.get("_active_command_source_package") or "")


def guarded_symbol_read_allowed(state, symbol: str) -> bool:
    if not active_command_is_extension(state):
        return True
    return extension_symbol_access_allowed(symbol)


def guarded_symbol_write_allowed(state, symbol: str) -> bool:
    if not active_command_is_extension(state):
        return True
    return extension_symbol_access_allowed(symbol)
