from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIRS = (
    PROJECT_ROOT / "system" / "layout" / "modules",
    PROJECT_ROOT / "extensions" / "layout" / "modules",
)

_REQUIRED_SYMBOLS = (
    "MODULE",
    "DEFAULT_PROMPT",
    "FOCUSABLE",
    "get_targets",
    "measure",
    "build_payload",
)

_MODULE_CACHE: dict[str, ModuleType] = {}
_PATH_CACHE: dict[str, Path] = {}
_META_CACHE: dict[str, dict[str, Any]] = {}


def _clean_name(module_name: str) -> str:
    clean = str(module_name or "").strip().lower()
    if not clean:
        raise ValueError("layout module name cannot be empty")
    if "/" in clean or "\\" in clean or clean.startswith("."):
        raise ValueError(f"invalid layout module name: {module_name}")
    return clean


def module_search_paths() -> list[str]:
    return [str(path) for path in MODULE_DIRS]


def module_path(module_name: str) -> Path:
    clean = _clean_name(module_name)
    cached = _PATH_CACHE.get(clean)
    if cached is not None:
        return cached
    for base in MODULE_DIRS:
        candidate = base / f"{clean}.py"
        if candidate.is_file():
            _PATH_CACHE[clean] = candidate
            return candidate
    raise ModuleNotFoundError(f"layout module not found: {clean}")


def _load_from_path(clean: str, path: Path) -> ModuleType:
    cache_key = clean
    cached = _MODULE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    spec = importlib.util.spec_from_file_location(f"aigmos_layout_module_{clean}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load layout module: {clean}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    for symbol in _REQUIRED_SYMBOLS:
        if not hasattr(module, symbol):
            raise ImportError(f"layout module {clean} missing required symbol: {symbol}")

    declared = str(getattr(module, "MODULE", "") or "").strip().lower()
    if declared != clean:
        raise ImportError(f"layout module {clean} has mismatched MODULE: {declared}")

    _MODULE_CACHE[cache_key] = module
    return module


def load_module(module_name: str) -> ModuleType:
    clean = _clean_name(module_name)
    path = module_path(clean)
    return _load_from_path(clean, path)


def invalidate_module_cache(module_name: str | None = None) -> None:
    if module_name is None:
        _MODULE_CACHE.clear()
        _PATH_CACHE.clear()
        _META_CACHE.clear()
        return
    clean = _clean_name(module_name)
    try:
        module_path(clean)
    except Exception:
        _PATH_CACHE.pop(clean, None)
        _META_CACHE.pop(clean, None)
        _MODULE_CACHE.pop(clean, None)
        return
    _MODULE_CACHE.pop(clean, None)
    _PATH_CACHE.pop(clean, None)
    _META_CACHE.pop(clean, None)


def module_meta(module_name: str) -> dict[str, Any]:
    clean = _clean_name(module_name)
    cached = _META_CACHE.get(clean)
    if cached is not None:
        return dict(cached)
    module = load_module(clean)
    meta = {
        "module": str(getattr(module, "MODULE", "") or "").strip().lower(),
        "default_prompt": str(getattr(module, "DEFAULT_PROMPT", "") or ""),
        "focusable": bool(getattr(module, "FOCUSABLE", False)),
    }
    _META_CACHE[clean] = dict(meta)
    return meta
