from __future__ import annotations

import importlib
from typing import Any, Callable

from system.extensions import ensure_extensions_tree, iter_package_module_names, reload_package_modules


_CORE_PACKAGE = "system.inputs"
_EXT_PACKAGE = "extensions.inputs"
_SKIP_MODULES = {"registry", "__init__"}


def _iter_input_modules() -> list[tuple[str, str, str]]:
    ensure_extensions_tree()

    discovered: dict[str, tuple[str, str, str]] = {}

    for package_name, source in ((_CORE_PACKAGE, "core"), (_EXT_PACKAGE, "extension")):
        for stem in iter_package_module_names(package_name):
            clean = str(stem or "").strip().lower()
            if not clean or clean in _SKIP_MODULES:
                continue
            discovered[clean] = (clean, package_name, source)

    return [discovered[name] for name in sorted(discovered.keys())]


def list_input_names() -> list[str]:
    return [name for name, _, _ in _iter_input_modules()]


def _resolve_factory(module, stem: str) -> Callable[..., Any]:
    factory = getattr(module, "create_input", None)
    if callable(factory):
        return factory

    explicit = getattr(module, "Input", None)
    if isinstance(explicit, type):
        return explicit

    candidates = []
    for attr_name in dir(module):
        value = getattr(module, attr_name)
        if isinstance(value, type) and attr_name.endswith("Input"):
            candidates.append((attr_name, value))

    if len(candidates) == 1:
        return candidates[0][1]

    preferred = f"{stem.capitalize()}Input"
    for attr_name, value in candidates:
        if attr_name == preferred:
            return value

    if candidates:
        return sorted(candidates, key=lambda item: item[0])[0][1]

    raise ValueError(f"input module has no factory/class: {module.__name__}")


def create_input(name: str, **kwargs: Any):
    clean = str(name or "").strip().lower()
    if not clean:
        raise ValueError("input name cannot be empty")

    for stem, package_name, _source in _iter_input_modules():
        if stem != clean:
            continue

        module = importlib.import_module(f"{package_name}.{stem}")
        factory = _resolve_factory(module, stem)
        return factory(**kwargs)

    raise ValueError(f"unknown input: {name}")



def reload_inputs() -> list[str]:
    reload_package_modules(_CORE_PACKAGE, _EXT_PACKAGE)
    return list_input_names()
