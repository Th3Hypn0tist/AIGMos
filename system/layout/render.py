from __future__ import annotations

from typing import Any

from . import registry
from .loader import load_module
from .lib.wrap import wrap_text

DEBUG_BORDERS = False


def _split_even(total: int, parts: int) -> list[int]:
    if parts <= 0:
        return []
    base = total // parts
    rem = total % parts
    return [base + (1 if i < rem else 0) for i in range(parts)]


def _round_percent(total: int, value: int) -> int:
    return int((int(total) * int(value)) / 100.0 + 0.5)


def _parse_percent(attrs: dict[str, Any], key: str) -> int | None:
    value = (attrs or {}).get(key)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _shrink_to_fit(total: int, mins: list[int]) -> list[int]:
    if total <= 0:
        return [0] * len(mins)
    out = [0] * len(mins)
    for i in range(min(len(mins), total)):
        out[i] = 1
    remaining = total - sum(out)
    needs = [max(0, int(mins[i]) - out[i]) for i in range(len(mins))]
    while remaining > 0 and any(n > 0 for n in needs):
        for i in range(len(needs)):
            if remaining <= 0:
                break
            if needs[i] > 0:
                out[i] += 1
                needs[i] -= 1
                remaining -= 1
    return out


def _distribute_min_scalable(total: int, infos: list[dict[str, Any]]) -> list[int]:
    mins = [int(info.get("min_h", 1) or 1) for info in infos]
    total_min = sum(mins)
    if total < total_min:
        return _shrink_to_fit(total, mins)
    out = mins[:]
    leftover = total - total_min
    scalable = [i for i, info in enumerate(infos) if bool(info.get("scalable_y"))]
    if leftover <= 0:
        return out
    if not scalable:
        if out:
            out[-1] += leftover
        return out
    base = leftover // len(scalable)
    rem = leftover % len(scalable)
    for n, i in enumerate(scalable):
        out[i] += base + (1 if n < rem else 0)
    return out


def _allocate_percent_primary(total: int, items: list[dict[str, Any]], attr_key: str, fill_infos: list[dict[str, Any]] | None = None, *, even_unspecified: bool = False) -> list[int]:
    sizes: list[int | None] = [None] * len(items)
    explicit: list[int] = []
    explicit_total = 0
    for i, item in enumerate(items):
        pct = _parse_percent(item.get("attrs") or {}, attr_key)
        if pct is None:
            continue
        size = _round_percent(total, pct)
        if pct > 0 and size <= 0:
            size = 1
        sizes[i] = size
        explicit.append(i)
        explicit_total += size
    unspecified = [i for i, size in enumerate(sizes) if size is None]
    leftover = total - explicit_total
    if leftover < 0:
        assigned = [int(sizes[i] or 0) for i in explicit]
        shrunk = _shrink_to_fit(total, assigned)
        for idx, new_size in zip(explicit, shrunk):
            sizes[idx] = new_size
        for idx in unspecified:
            sizes[idx] = 0
        return [int(size or 0) for size in sizes]
    if not unspecified:
        if sizes and leftover > 0:
            sizes[-1] = int(sizes[-1] or 0) + leftover
        return [int(size or 0) for size in sizes]
    if even_unspecified:
        distributed = _split_even(leftover, len(unspecified))
    else:
        infos = [fill_infos[i] for i in unspecified] if fill_infos else [{"min_h": 1, "scalable_y": True}] * len(unspecified)
        distributed = _distribute_min_scalable(leftover, infos)
    for idx, size in zip(unspecified, distributed):
        sizes[idx] = size
    return [int(size or 0) for size in sizes]


def _text_contract(text: str, width: int) -> dict[str, Any]:
    return {"min_h": len(wrap_text(text, width)), "scalable_y": False}


def _leaf_contract(ctx, spec: dict[str, Any], binding_handle: str, width: int) -> dict[str, Any]:
    module = spec.get("_module") or load_module(str(spec.get("tag") or ""))
    instance = spec.get("instance")
    if instance is None and "instance_handle" in spec:
        instance = registry.get_instance(ctx, spec["instance_handle"])
        spec["instance"] = instance
    attrs = dict(spec.get("attrs") or {})
    bordered = str(attrs.get("border") or "").strip().lower() in {"1", "true", "yes", "on"}
    inner_width = max(1, int(width) - 2) if bordered else width
    info = dict(module.measure(ctx, binding_handle, spec, inner_width, instance) or {"min_h": 1, "scalable_y": False})
    if bordered:
        info["min_h"] = int(info.get("min_h", 1) or 1) + 2
    return info


def _child_contract(ctx, child: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, width: int) -> dict[str, Any]:
    kind = str(child.get("type") or "")
    if kind == "text":
        return _text_contract(str(child.get("value") or ""), width)
    if kind == "leaf_ref":
        return _leaf_contract(ctx, module_specs[int(child["index"])], binding_handle, width)
    if kind == "row":
        return _row_contract(ctx, child, module_specs, binding_handle, width)
    raise ValueError(f"unknown child type: {kind}")


def _cell_contract(ctx, cell: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, width: int) -> dict[str, Any]:
    inner_w = max(1, int(width) - 2) if DEBUG_BORDERS else max(1, int(width))
    infos = [_child_contract(ctx, child, module_specs, binding_handle, inner_w) for child in cell.get("children") or []]
    content_min = sum(int(info.get("min_h", 1) or 1) for info in infos) if infos else 1
    scalable = any(bool(info.get("scalable_y")) for info in infos) if infos else False
    return {"min_h": content_min + (2 if DEBUG_BORDERS else 0), "scalable_y": scalable}


def _allocate_cell_widths(row: dict[str, Any], total_w: int) -> list[int]:
    cells = list(row.get("cells") or [])
    return _allocate_percent_primary(total_w, cells, "w", [{"min_h": 1, "scalable_y": True}] * len(cells), even_unspecified=True)


def _row_contract(ctx, row: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, width: int) -> dict[str, Any]:
    cell_widths = _allocate_cell_widths(row, width)
    infos = [_cell_contract(ctx, cell, module_specs, binding_handle, max(1, cell_width)) for cell, cell_width in zip(row.get("cells") or [], cell_widths)]
    return {"min_h": max((int(info.get("min_h", 1) or 1) for info in infos), default=0), "scalable_y": any(bool(info.get("scalable_y")) for info in infos)}


def _allocate_row_heights(ctx, rows: list[dict[str, Any]], module_specs: dict[int, dict[str, Any]], binding_handle: str, total_h: int, total_w: int) -> list[int]:
    infos = [_row_contract(ctx, row, module_specs, binding_handle, total_w) for row in rows]
    return _allocate_percent_primary(total_h, rows, "h", infos, even_unspecified=False)


def _render_module_payload(ctx, binding_handle: str, spec: dict[str, Any], rect: dict[str, int]) -> dict[str, Any]:
    module = spec.get("_module") or load_module(str(spec.get("tag") or ""))
    instance = spec.get("instance")
    if instance is None and "instance_handle" in spec:
        instance = registry.get_instance(ctx, spec["instance_handle"])
        spec["instance"] = instance
    return dict(module.build_payload(ctx, binding_handle, spec, rect, instance) or {"lines": [""], "align": "left", "va": "bottom"})


def _plan_leaf(ctx, binding_handle: str, spec: dict[str, Any], drawables: list[dict[str, Any]], x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return
    rect = {"x": x, "y": y, "w": w, "h": h}
    spec["rect"] = rect
    payload = _render_module_payload(ctx, binding_handle, spec, rect)
    spec["_last_payload"] = payload
    item = {"rect": rect, "payload": payload}
    if "instance_handle" in spec:
        item["module_handle"] = spec["instance_handle"]
    drawables.append(item)


def _plan_text(drawables: list[dict[str, Any]], text: str, x: int, y: int, w: int, h: int) -> None:
    drawables.append({"rect": {"x": x, "y": y, "w": w, "h": h}, "payload": {"lines": wrap_text(text, max(1, w)), "align": "left", "va": "bottom"}})


def _plan_child(ctx, child: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, drawables: list[dict[str, Any]], x: int, y: int, w: int, h: int) -> None:
    if h <= 0 or w <= 0:
        return
    kind = str(child.get("type") or "")
    if kind == "text":
        _plan_text(drawables, str(child.get("value") or ""), x, y, w, h)
    elif kind == "leaf_ref":
        _plan_leaf(ctx, binding_handle, module_specs[int(child["index"])], drawables, x, y, w, h)
    elif kind == "row":
        _plan_row(ctx, child, module_specs, binding_handle, drawables, x, y, w, h)


def _plan_cell(ctx, cell: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, drawables: list[dict[str, Any]], x: int, y: int, w: int, h: int) -> None:
    if w <= 0 or h <= 0:
        return
    inner_x, inner_y, inner_w, inner_h = (x + 1, y + 1, max(0, w - 2), max(0, h - 2)) if DEBUG_BORDERS else (x, y, w, h)
    if inner_w <= 0 or inner_h <= 0:
        return
    infos = [_child_contract(ctx, child, module_specs, binding_handle, inner_w) for child in cell.get("children") or []]
    heights = _distribute_min_scalable(inner_h, infos)
    cy = inner_y
    for child, child_h in zip(cell.get("children") or [], heights):
        _plan_child(ctx, child, module_specs, binding_handle, drawables, inner_x, cy, inner_w, child_h)
        cy += child_h


def _plan_row(ctx, row: dict[str, Any], module_specs: dict[int, dict[str, Any]], binding_handle: str, drawables: list[dict[str, Any]], x: int, y: int, w: int, h: int) -> None:
    widths = _allocate_cell_widths(row, w)
    cx = x
    for cell, cell_w in zip(row.get("cells") or [], widths):
        _plan_cell(ctx, cell, module_specs, binding_handle, drawables, cx, y, cell_w, h)
        cx += cell_w


def _binding_module_specs(ctx, handle: str) -> list[dict[str, Any]]:
    runtime = ctx.setdefault("layout_runtime", {}) if isinstance(ctx, dict) else {}
    binding = runtime.get("bindings", {}).get(registry.normalize_handle(handle))
    if not binding:
        return []
    modules = list(binding.get("modules") or [])
    if not modules:
        modules = list(registry._ensure_layout_binding_runtime(ctx, handle) or [])
    by_handle = {inst.handle: inst for inst in (registry.get_instance(ctx, item) for item in modules)}
    module_cache = {name: load_module(name) for name in {str(inst.MODULE or "").strip().lower() for inst in by_handle.values()}}
    specs: list[dict[str, Any]] = []
    for spec in binding.get("specs") or []:
        tag = str(spec.get("tag") or "").strip().lower()
        cloned = dict(spec)
        if tag in registry._IGNORE_BOUND_TAGS:
            cloned["_module"] = load_module(tag)
            specs.append(cloned)
            continue
        child_handle = registry._instance_handle(binding["handle"], spec)
        inst = by_handle.get(child_handle)
        cloned["instance_handle"] = child_handle
        cloned["instance"] = inst
        cloned["_module"] = module_cache.get(str(inst.MODULE or "").strip().lower()) if inst is not None else load_module(tag)
        specs.append(cloned)
    return specs


def _single_instance_layout(ctx, handle: str) -> dict[str, Any]:
    inst = registry.get_instance(ctx, handle)
    return {"tree": {"type": "layout", "attrs": {}, "rows": [{"type": "row", "attrs": {}, "cells": [{"type": "cell", "attrs": {}, "children": [{"type": "leaf_ref", "index": 0}]}]}]}, "specs": [{"tag": inst.MODULE, "attrs": {}, "ordinal": 1, "instance_handle": inst.handle, "render_index": 0}]}


def _cursor_from_cs_spec(spec: dict[str, Any]) -> dict[str, int] | None:
    rect = spec.get("rect")
    payload = spec.get("_last_payload") or {}
    local = payload.get("cursor_local") if isinstance(payload, dict) else None
    if str(spec.get("tag") or "").strip().lower() != "cs" or not isinstance(rect, dict) or not isinstance(local, dict):
        return None
    return {"x": int(rect.get("x", 0)) + max(0, min(int(rect.get("w", 1)) - 1, int(local.get("x", 0) or 0))), "y": int(rect.get("y", 0)) + max(0, min(int(rect.get("h", 1)) - 1, int(local.get("y", 0) or 0)))}


def _screen_cache(ctx) -> dict[str, Any]:
    runtime = ctx.setdefault("layout_runtime", {}) if isinstance(ctx, dict) else {}
    return runtime.setdefault("screen_cache", {})


def _build_full_snapshot(ctx, active: str, width: int, height: int) -> dict[str, Any]:
    if registry.has_layout_binding(ctx, active):
        runtime = ctx.setdefault("layout_runtime", {}) if isinstance(ctx, dict) else {}
        binding = runtime.get("bindings", {}).get(registry.normalize_handle(active), {})
        tree_root = dict(binding.get("tree") or {}).get("tree") or {"type": "layout", "attrs": {}, "rows": []}
        specs = _binding_module_specs(ctx, active)
        binding_handle = registry.normalize_handle(active)
    else:
        single = _single_instance_layout(ctx, active)
        tree_root = single["tree"]
        specs = single["specs"]
        binding_handle = registry.normalize_handle(active)
    module_specs = {int(spec.get("render_index", idx)): spec for idx, spec in enumerate(specs)}
    rows = list(tree_root.get("rows") or [])
    row_heights = _allocate_row_heights(ctx, rows, module_specs, binding_handle, height, width)
    drawables: list[dict[str, Any]] = []
    cy = 0
    for row, row_h in zip(rows, row_heights):
        _plan_row(ctx, row, module_specs, binding_handle, drawables, 0, cy, width, row_h)
        cy += row_h
    focused = registry.get_focused_module_handle(ctx)
    focused_spec = next((item for item in specs if item.get("instance_handle") == focused), None) if focused else None
    by_handle = {item.get("instance_handle"): item for item in specs if item.get("instance_handle")}
    snapshot = {
        "active_handle": active,
        "drawables": drawables,
        "changed_drawables": list(drawables),
        "cursor": _cursor_from_cs_spec(focused_spec) if focused_spec else None,
        "focused_module": focused,
        "full_redraw": True,
    }
    _screen_cache(ctx)["current"] = {
        "key": (active, width, height),
        "active_handle": active,
        "width": width,
        "height": height,
        "drawables": drawables,
        "specs": specs,
        "spec_by_handle": by_handle,
        "cursor": snapshot["cursor"],
        "focused_module": focused,
        "snapshot": snapshot,
    }
    return snapshot


def build_snapshot(ctx, width: int | None = None, height: int | None = None) -> dict[str, Any]:
    registry.bootstrap(ctx)
    if isinstance(ctx, dict):
        ctx["_layout_frame_cache"] = {}
    try:
        active = registry.get_active_handle(ctx)
        width = max(1, int(width or 1))
        height = max(1, int(height or 1))
        flags = ctx.setdefault("flags", {}) if isinstance(ctx, dict) else {}
        cache = _screen_cache(ctx).get("current")
        dirty_modules = set(flags.pop("layout_dirty_modules", set()) or set())
        hard_redraw = bool(flags.pop("layout_hard_redraw", False))
        cache_key = (active, width, height)
        if hard_redraw or not isinstance(cache, dict) or tuple(cache.get("key") or ()) != cache_key:
            return _build_full_snapshot(ctx, active, width, height)

        if not dirty_modules:
            return _build_full_snapshot(ctx, active, width, height)

        drawables = cache.get("drawables") or []
        spec_by_handle = cache.get("spec_by_handle") or {}
        changed: list[dict[str, Any]] = []
        for item in drawables:
            module_handle = str(item.get("module_handle") or "")
            if module_handle not in dirty_modules:
                continue
            spec = spec_by_handle.get(module_handle)
            rect = item.get("rect") or {}
            if not spec or not rect:
                continue
            previous_payload = item.get("payload") if isinstance(item.get("payload"), dict) else None
            payload = _render_module_payload(ctx, active, spec, rect)
            spec["_last_payload"] = payload
            item["payload"] = payload
            changed.append({
                "rect": rect,
                "payload": payload,
                "module_handle": module_handle,
                "prev_payload": previous_payload,
            })

        focused = registry.get_focused_module_handle(ctx)
        focused_spec = spec_by_handle.get(focused) if focused else None
        cursor = _cursor_from_cs_spec(focused_spec) if focused_spec else None
        cache["cursor"] = cursor
        cache["focused_module"] = focused
        snapshot = {
            "active_handle": active,
            "drawables": drawables,
            "changed_drawables": changed,
            "cursor": cursor,
            "focused_module": focused,
            "full_redraw": False,
        }
        cache["snapshot"] = snapshot
        return snapshot
    finally:
        if isinstance(ctx, dict):
            ctx.pop("_layout_frame_cache", None)


def push_live_line(ctx, text: Any) -> None:
    flags = ctx.setdefault("flags", {}) if isinstance(ctx, dict) else {}
    flags["force_render"] = True
    flags["layout_hard_redraw"] = True
