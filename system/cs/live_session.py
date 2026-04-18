from __future__ import annotations

from typing import Any

from system.cs.live_packet import consume_live_packet, get_live_packet, set_live_packet


_SESSION_BASE_DEFAULTS: dict[str, Any] = {
    "state": "idle",
    "done": 1,
    "error": "",
}


def _session_defaults(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(_SESSION_BASE_DEFAULTS)
    if isinstance(defaults, dict):
        merged.update(defaults)
    return merged


def read_live_session(parser, name: str, *, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    return get_live_packet(parser, name, defaults=_session_defaults(defaults))


def open_live_session(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    payload = {"state": "open", "done": 0, "error": ""}
    payload.update(fields)
    return set_live_packet(parser, name, defaults=_session_defaults(defaults), bump_seq=bump_seq, **payload)


def chunk_live_session(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = True,
    clear_error: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    payload = {"state": "open", "done": 0}
    if clear_error:
        payload["error"] = ""
    payload.update(fields)
    return set_live_packet(parser, name, defaults=_session_defaults(defaults), bump_seq=bump_seq, **payload)


def done_live_session(
    parser,
    name: str,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    payload = {"state": "done", "done": 1, "error": ""}
    payload.update(fields)
    return set_live_packet(parser, name, defaults=_session_defaults(defaults), bump_seq=bump_seq, **payload)


def fail_live_session(
    parser,
    name: str,
    error: Any,
    *,
    defaults: dict[str, Any] | None = None,
    bump_seq: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    payload = {
        "state": "error",
        "done": 1,
        "error": "" if error is None else str(error),
    }
    payload.update(fields)
    return set_live_packet(parser, name, defaults=_session_defaults(defaults), bump_seq=bump_seq, **payload)


def consume_live_session(
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
    return consume_live_packet(
        parser,
        name,
        defaults=_session_defaults(defaults),
        done_field=done_field,
        value_field=value_field,
        error_field=error_field,
        seq_field=seq_field,
        emit_seq_field=emit_seq_field,
    )
