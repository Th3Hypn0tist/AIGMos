from __future__ import annotations

from typing import Any

from system.cs.runtime_ctx import get_runtime, set_runtime


_BASE_DEFAULTS: dict[str, Any] = {
    "seq": 0,
    "emit_seq": 0,
}


def packet_runtime_key(name: str) -> str:
    clean = str(name or "").strip()
    if not clean:
        raise ValueError("live packet name required")
    return f"live_packet:{clean}"


def _merged_defaults(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(_BASE_DEFAULTS)
    if isinstance(defaults, dict):
        merged.update(defaults)
    return merged


def ensure_live_packet(parser, name: str, *, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime_key = packet_runtime_key(name)
    wanted = _merged_defaults(defaults)
    current = get_runtime(parser, runtime_key, None)

    if isinstance(current, dict):
        item = dict(wanted)
        item.update(current)
        if item != current:
            set_runtime(parser, runtime_key, item)
        return item

    set_runtime(parser, runtime_key, wanted)
    return dict(wanted)


def get_live_packet(parser, name: str, *, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    return dict(ensure_live_packet(parser, name, defaults=defaults))


def set_live_packet(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = False,
    **fields: Any,
) -> dict[str, Any]:
    runtime_key = packet_runtime_key(name)
    item = dict(ensure_live_packet(parser, name, defaults=defaults))

    if bump_seq:
        item["seq"] = int(item.get("seq") or 0) + 1

    for key, value in fields.items():
        item[key] = value

    set_runtime(parser, runtime_key, item)
    return item


def clear_live_packet(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = False,
    **overrides: Any,
) -> dict[str, Any]:
    item = _merged_defaults(defaults)
    if bump_seq:
        item["seq"] = int(item.get("seq") or 0) + 1
    if overrides:
        item.update(overrides)
    set_runtime(parser, packet_runtime_key(name), item)
    return item


def consume_live_packet(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    done_field: str = "done",
    value_field: str = "response",
    error_field: str = "error",
    seq_field: str = "seq",
    emit_seq_field: str = "emit_seq",
) -> Any:
    item = get_live_packet(parser, name, defaults=defaults)

    if int(item.get(done_field) or 0) != 1:
        return None

    seq = int(item.get(seq_field) or 0)
    emit_seq = int(item.get(emit_seq_field) or 0)
    if seq <= 0 or seq == emit_seq:
        return None

    item[emit_seq_field] = seq
    set_runtime(parser, packet_runtime_key(name), item)

    error = item.get(error_field)
    if isinstance(error, str) and error.strip():
        return error.strip()
    if error not in (None, ""):
        return error

    value = item.get(value_field)
    if value in (None, ""):
        return None
    return value
