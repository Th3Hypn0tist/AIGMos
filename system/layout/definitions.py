from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .parser import parse_template

_LAYOUT_DIRS = (
    Path(__file__).resolve().parents[1] / "library" / "layout",
    Path(__file__).resolve().parents[2] / "extensions" / "layout",
)

_CONTAINER_TAGS = {"layout", "row", "cell"}
_ATTR_RE = re.compile(
    r"""([A-Za-z_][A-Za-z0-9_:\-.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))"""
)
_LEAF_RE = re.compile(
    r"^\s*<\s*([A-Za-z_][A-Za-z0-9_-]*)(?P<attrs>.*?)\s*>\s*$",
    re.DOTALL,
)


def _leaf_tag(raw: str) -> str:
    m = re.match(r"\s*<\s*([A-Za-z_][A-Za-z0-9_-]*)", str(raw or ""))
    if not m:
        return ""
    return m.group(1).strip().lower()



def _leaf_elem(raw: str) -> ET.Element:
    text = str(raw or "").strip()
    if text.endswith("/>"):
        raise ET.ParseError("self-closing leaf tags are not allowed")
    match = _LEAF_RE.match(text)
    if not match:
        raise ET.ParseError("not well-formed leaf tag")

    tag = str(match.group(1) or "").strip()
    attrs_text = str(match.group("attrs") or "")
    attrs: dict[str, str] = {}
    consumed: list[tuple[int, int]] = []

    for item in _ATTR_RE.finditer(attrs_text):
        key = str(item.group(1) or "").strip()
        value = item.group(2)
        if value is None:
            value = item.group(3)
        if value is None:
            value = item.group(4)
        attrs[key] = "" if value is None else str(value)
        consumed.append(item.span())

    leftovers: list[str] = []
    cursor = 0
    for start, end in consumed:
        leftovers.append(attrs_text[cursor:start])
        cursor = end
    leftovers.append(attrs_text[cursor:])
    remainder = "".join(leftovers).strip()
    if remainder:
        raise ET.ParseError("not well-formed leaf attributes")

    return ET.Element(tag, attrs)






def _resolve_layout_path(name: str) -> Path:
    token = str(name or "").strip()
    if token.startswith("/"):
        token = token[1:]
    if not token:
        raise FileNotFoundError("layout not found")

    direct = Path(token)
    if direct.exists() and direct.is_file():
        return direct

    candidates = [token]
    if not token.endswith(".tmpl"):
        candidates.append(f"{token}.tmpl")

    for base in _LAYOUT_DIRS:
        for candidate in candidates:
            path = base / candidate
            if path.exists() and path.is_file():
                return path

    raise FileNotFoundError(f"layout not found: {name}")



def parse_layout_definition(name: str) -> dict[str, Any]:
    path = _resolve_layout_path(name)
    text = path.read_text(encoding="utf-8")
    parsed = parse_template(text)
    return {
        "name": path.stem,
        "path": str(path),
        "tree": parsed["tree"],
        "modules": parsed["modules"],
    }



def flatten_module_specs(tree: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen_ids: dict[str, set[str]] = {}
    writable_requires_id = {'q'}

    for item in tree.get("modules") or []:
        raw = str(item.get("raw") or "")
        tag = _leaf_tag(raw)
        if not tag or tag in _CONTAINER_TAGS:
            continue
        elem = _leaf_elem(raw)
        attrs = dict(elem.attrib)
        counts[tag] = counts.get(tag, 0) + 1
        module_id = str(attrs.get('id') or '').strip()
        if tag in writable_requires_id and not module_id:
            raise ValueError(f"layout module <{tag}> requires id")
        if module_id:
            bucket = seen_ids.setdefault(tag, set())
            if module_id in bucket:
                raise ValueError(f"duplicate module id for <{tag}>: {module_id}")
            bucket.add(module_id)
        specs.append(
            {
                "tag": tag,
                "raw": raw,
                "attrs": attrs,
                "module_id": module_id,
                "render_index": int(item.get("render_index", len(specs))),
                "ordinal": counts[tag],
            }
        )

    return specs
