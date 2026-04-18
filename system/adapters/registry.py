from __future__ import annotations

import importlib
from typing import Any, Callable

from system.extensions import ensure_extensions_tree, iter_package_module_names, reload_package_modules


_CORE_PACKAGE = "system.adapters"
_EXT_PACKAGE = "extensions.adapters"
_SKIP_MODULES = {"osc", "registry", "__init__"}


def _iter_adapter_modules() -> list[tuple[str, str, str]]:
    ensure_extensions_tree()

    discovered: dict[str, tuple[str, str, str]] = {}

    for package_name, source in ((_CORE_PACKAGE, "core"), (_EXT_PACKAGE, "extension")):
        for stem in iter_package_module_names(package_name):
            clean = str(stem or "").strip().lower()
            if not clean or clean in _SKIP_MODULES:
                continue
            discovered[clean] = (clean, package_name, source)

    return [discovered[name] for name in sorted(discovered.keys())]


def list_adapter_names() -> list[str]:
    return [name for name, _, _ in _iter_adapter_modules()]


def _resolve_factory(module, stem: str) -> Callable[..., Any]:
    factory = getattr(module, "create_adapter", None)
    if callable(factory):
        return factory

    explicit = getattr(module, "Adapter", None)
    if isinstance(explicit, type):
        return explicit

    candidates = []
    for attr_name in dir(module):
        value = getattr(module, attr_name)
        if isinstance(value, type) and attr_name.endswith("Adapter"):
            candidates.append((attr_name, value))

    if len(candidates) == 1:
        return candidates[0][1]

    preferred = f"{stem.capitalize()}Adapter"
    for attr_name, value in candidates:
        if attr_name == preferred:
            return value

    if candidates:
        return sorted(candidates, key=lambda item: item[0])[0][1]

    raise ValueError(f"adapter module has no factory/class: {module.__name__}")


def create_adapter(name: str, **kwargs: Any):
    clean = str(name or "").strip().lower()
    if not clean:
        raise ValueError("adapter name cannot be empty")

    for stem, package_name, _source in _iter_adapter_modules():
        if stem != clean:
            continue

        module = importlib.import_module(f"{package_name}.{stem}")
        factory = _resolve_factory(module, stem)
        return factory(**kwargs)

    raise ValueError(f"unknown adapter: {name}")


def _route_specs_from_config(config: dict | None) -> list[dict[str, Any]]:
    if not isinstance(config, dict):
        return []

    state_cfg = config.get("state")
    if not isinstance(state_cfg, dict):
        return []

    routes = state_cfg.get("routes")
    if not isinstance(routes, list):
        return []

    out: list[dict[str, Any]] = []
    for item in routes:
        if not isinstance(item, dict):
            continue
        prefix = str(item.get("prefix") or "").strip()
        adapter = str(item.get("adapter") or "").strip().lower()
        adapter_config = item.get("config") if isinstance(item.get("config"), dict) else {}
        if not prefix or not adapter:
            continue
        out.append({
            "prefix": prefix,
            "adapter": adapter,
            "config": dict(adapter_config),
        })
    return out


def build_state_request(default_adapter, config: dict | None = None):
    from system.state.request import StateRequest

    request = StateRequest(default_adapter)

    mem_adapter = create_adapter("mem")
    request.register_route("$MEM", mem_adapter)
    request.register_route("#OSC", mem_adapter)

    extras = build_extra_routes(config)
    for prefix, adapter in extras:
        request.register_route(prefix, adapter)

    return request, mem_adapter, extras



def reload_adapters() -> list[str]:
    reload_package_modules(_CORE_PACKAGE, _EXT_PACKAGE)
    return list_adapter_names()



def build_extra_routes(config: dict | None = None) -> list[tuple[str, Any]]:
    extras: list[tuple[str, Any]] = []
    for spec in _route_specs_from_config(config):
        adapter = create_adapter(spec["adapter"], **spec["config"])
        extras.append((spec["prefix"], adapter))
    return extras
