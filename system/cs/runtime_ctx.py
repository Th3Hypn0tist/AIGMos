from __future__ import annotations

from typing import Any


def runtime_map(parser) -> dict[str, Any]:
    runtime = getattr(parser, 'runtime', None)
    if isinstance(runtime, dict):
        return runtime
    runtime = {}
    parser.runtime = runtime
    return runtime


def get_runtime(parser, key: str, default: Any = None) -> Any:
    return runtime_map(parser).get(key, default)


def set_runtime(parser, key: str, value: Any) -> Any:
    runtime_map(parser)[key] = value
    return value


def get_ctx(parser) -> dict[str, Any]:
    ctx = get_runtime(parser, 'ctx', None)
    return ctx if isinstance(ctx, dict) else {}


def set_ctx_config(parser, config: Any) -> None:
    ctx = get_ctx(parser)
    if ctx:
        ctx['config'] = config


def get_flags(parser) -> dict[str, Any] | None:
    flags = get_runtime(parser, 'flags', None)
    return flags if isinstance(flags, dict) else None


def set_flag(parser, name: str, value: Any) -> None:
    flags = get_flags(parser)
    if flags is not None:
        flags[name] = value


def force_render(parser) -> None:
    parser.force_render = True
    set_flag(parser, 'force_render', True)


def set_running(parser, value: bool) -> None:
    set_flag(parser, 'running', bool(value))


def get_layout_caller_handle(parser) -> str:
    return str(get_runtime(parser, 'layout_caller_handle', '') or '').strip()


def get_triggers(parser):
    return get_runtime(parser, 'triggers', None)


def get_events(parser):
    return get_runtime(parser, 'events', None)


def get_trigger_bus(parser):
    return get_runtime(parser, 'trigger_bus', None)
