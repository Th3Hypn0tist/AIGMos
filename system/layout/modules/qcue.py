from __future__ import annotations

from typing import Any

from system.layout.lib.border import content_rect
from system.layout.lib.payload import finalize_payload
from system.layout.lib.scroll import handle_scroll_key, viewport_head, viewport_tail
from system.layout.lib.spec import flow_attr
from system.layout.lib.wrap import wrap_text
from system.lib.q.qcue import QCUE_ROOT, qcue_state_get

MODULE = "qcue"
DEFAULT_PROMPT = "cs> "
FOCUSABLE = True


def get_targets(handle: str, config: dict[str, Any] | None = None) -> tuple[str, str]:
    return QCUE_ROOT, QCUE_ROOT


def measure(ctx, binding_handle: str, spec: dict[str, Any], width: int, instance) -> dict[str, Any]:
    return {"min_h": 1, "scalable_y": True}


def _sorted_numeric_items(value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, list):
        return [(str(idx), item) for idx, item in enumerate(value)]
    if not isinstance(value, dict):
        return []

    def sort_key(pair: tuple[str, Any]) -> tuple[int, int | str]:
        key = str(pair[0] or "")
        return (0, int(key)) if key.isdigit() else (1, key)

    return sorted(((str(key), item) for key, item in value.items()), key=sort_key)


def _task_id_rank(task_id: Any) -> tuple[int, int | str]:
    text = str(task_id or "").strip()
    return (0, int(text)) if text.isdigit() else (1, text)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _effective_q_active_task_id(active: dict[str, Any]) -> str:
    best_task_id = ''
    best_rank: tuple[int, int | str] | None = None
    for _root, raw in dict(active or {}).items():
        entry = dict(raw or {})
        task_id = str(entry.get('task_id') or '').strip()
        if not task_id:
            continue
        rank = _task_id_rank(task_id)
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_task_id = task_id
    return best_task_id


def _kind_filter(attrs: dict[str, Any]) -> str:
    raw = str(attrs.get("kind") or attrs.get("show") or "all").strip().lower()
    return raw if raw in {"q", "qc", "all"} else "all"


def _alias_filter(attrs: dict[str, Any]) -> str:
    return str(attrs.get("alias") or "").strip()


def _target_filter(attrs: dict[str, Any]) -> str:
    return str(attrs.get("target") or attrs.get("qtarget") or "").strip()


def _matches(task: dict[str, Any], *, kind: str, alias: str, target: str) -> bool:
    task_kind = str(task.get("kind") or "q").strip().lower() or "q"
    task_alias = str(task.get("alias") or "").strip()
    task_root = str(task.get("q_root") or "").strip()
    if kind != "all" and task_kind != kind:
        return False
    if alias and task_alias != alias:
        return False
    if target and task_root != target:
        return False
    return True


def _identity_text(task: dict[str, Any]) -> str:
    task_kind = str(task.get("kind") or "q").strip().lower() or "q"
    if task_kind == "qc":
        identity = str(task.get("caller_handle") or "").strip()
        if identity:
            return identity
        output_symbol = str(task.get("output_symbol") or "").strip()
        if output_symbol:
            return output_symbol
        return "qc"
    identity = str(task.get("q_root") or "").strip()
    if identity:
        return identity
    caller = str(task.get("caller_handle") or "").strip()
    return caller or "q"


def _status_prefix(task: dict[str, Any], pos: int, total: int) -> str:
    status = str(task.get("status") or "").strip().lower()
    if status == "running":
        return "[RUN]"
    if total > 0:
        return f"[CUE {pos}/{total}]"
    return "[WAITING]"


def _line_text(task: dict[str, Any], pos: int, total: int) -> str:
    task_kind = str(task.get("kind") or "q").strip().lower() or "q"
    prefix = _status_prefix(task, pos, total)
    identity = _identity_text(task)
    return f"{prefix} {task_kind} {identity}".rstrip()


def _collect_lines(ctx, attrs: dict[str, Any]) -> list[str]:
    state = ctx.get("state") if isinstance(ctx, dict) else None
    data = qcue_state_get(state)
    aliases = dict(data.get("aliases") or {})
    active = dict(data.get("active") or {})

    kind = _kind_filter(attrs)
    alias_filter = _alias_filter(attrs)
    target_filter = _target_filter(attrs)

    rows: list[tuple[tuple[int, int | str], int, int, dict[str, Any]]] = []
    effective_q_active_task_id = _effective_q_active_task_id(active)

    for alias_name in sorted(str(name) for name in aliases.keys()):
        alias_data = aliases.get(alias_name) if isinstance(aliases.get(alias_name), dict) else {}
        queue_items = _sorted_numeric_items(alias_data.get("queue"))
        queue_total = len(queue_items)
        for pos, (_key, item) in enumerate(queue_items, start=1):
            if not isinstance(item, dict):
                continue
            task = dict(item)
            task.setdefault("alias", alias_name)
            task_kind = str(task.get("kind") or "q").strip().lower() or "q"
            task_root = str(task.get("q_root") or "").strip()
            task_id = str(task.get("task_id") or "")
            if task_kind == "q":
                if effective_q_active_task_id and task_id == effective_q_active_task_id:
                    task["status"] = "running"
                elif str(task.get("status") or "").strip().lower() == "running":
                    task["status"] = "waiting"
            if not _matches(task, kind=kind, alias=alias_filter, target=target_filter):
                continue
            rows.append((_task_id_rank(task.get("task_id")), pos, queue_total, task))

    rows.sort(key=lambda row: row[0])
    if not rows:
        return ["[QUEUE EMPTY]"]
    return [_line_text(task, pos, total) for _rank, pos, total, task in rows]


def _visible_lines(ctx, module_handle: str, lines: list[str], width: int, height: int, flow: str) -> list[str]:
    from system.layout import input as layout_input

    ui = layout_input.get_module_ui(ctx, module_handle)
    follow = bool(ui.get("follow", True))
    scroll = max(0, int(ui.get("scroll", 0) or 0))

    wrapped: list[str] = []
    for raw in lines or [""]:
        wrapped.extend(wrap_text(_clean_text(raw), width) or [""])
    if not wrapped:
        wrapped = [""]

    if follow:
        ui["scroll"] = 0
        if flow == "top":
            return viewport_head(wrapped, height, 0)
        return viewport_tail(wrapped, height, 0)

    if flow == "top":
        return viewport_head(wrapped, height, scroll)
    return viewport_tail(wrapped, height, scroll)


def build_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int], instance):
    attrs = dict(spec.get("attrs") or {})
    flow = flow_attr(MODULE, attrs)
    inner_rect = content_rect(attrs, rect)
    lines = _collect_lines(ctx, attrs)
    visible = _visible_lines(
        ctx,
        instance.handle,
        lines,
        max(1, int(inner_rect.get("w", 1) or 1)),
        max(1, int(inner_rect.get("h", 1) or 1)),
        flow,
    )
    payload_attrs = dict(attrs)
    if not str(payload_attrs.get("flow") or "").strip():
        payload_attrs["flow"] = "top"
    return finalize_payload(ctx, instance.handle, visible or [""], payload_attrs, MODULE, rect)


def handle_key(ctx, module_handle: str, key: int) -> bool:
    from system.layout import input as layout_input

    ui = layout_input.get_module_ui(ctx, module_handle)
    if handle_scroll_key(ui, key, kind="q"):
        layout_input._mark_dirty(ctx)
        return True
    return False


def clear(ctx, module_handle: str, instance):
    from system.layout import input as layout_input

    ui = layout_input.get_module_ui(ctx, module_handle)
    ui["follow"] = True
    ui["scroll"] = 0
    return True
