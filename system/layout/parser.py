import re
import xml.etree.ElementTree as ET


CONTAINERS = {"layout", "row", "cell"}
TAG_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_-]*)(\s+[^>]*)?>", re.IGNORECASE)


def _norm(text):
    if text is None:
        return ""
    return " ".join(text.split()).strip()


def _tokenize_modules(src):
    modules = []

    def repl(match):
        tag = match.group(1)
        if tag in CONTAINERS:
            return match.group(0)

        i = len(modules)
        modules.append({
            "render_index": i,
            "raw": match.group(0),
        })
        return f'<leaf i="{i}"/>'

    return TAG_RE.sub(repl, src), modules


def _parse_content(elem):
    out = []

    head = _norm(elem.text)
    if head:
        out.append({"type": "text", "value": head})

    for child in elem:
        if child.tag == "row":
            out.append(_parse_row(child))
        elif child.tag == "leaf":
            out.append({"type": "leaf_ref", "index": int(child.attrib["i"])})
        else:
            raise ValueError(f"invalid tag inside <cell>: <{child.tag}>")

        tail = _norm(child.tail)
        if tail:
            out.append({"type": "text", "value": tail})

    return out


def _parse_cell(elem):
    return {
        "type": "cell",
        "attrs": dict(elem.attrib),
        "children": _parse_content(elem),
    }


def _parse_row(elem):
    direct_cells = [child for child in elem if child.tag == "cell"]

    if direct_cells:
        if _norm(elem.text):
            raise ValueError("<row> with direct <cell> children cannot contain direct text")

        for child in elem:
            if child.tag != "cell":
                raise ValueError(
                    f"<row> with direct <cell> children cannot also contain <{child.tag}>"
                )
            if _norm(child.tail):
                raise ValueError("<row> with direct <cell> children cannot contain tail text")

        return {
            "type": "row",
            "attrs": dict(elem.attrib),
            "cells": [_parse_cell(child) for child in direct_cells],
        }

    return {
        "type": "row",
        "attrs": dict(elem.attrib),
        "cells": [{
            "type": "cell",
            "attrs": {},
            "children": _parse_content(elem),
        }],
    }


def parse_template(template_text):
    src = template_text.strip()
    src, modules = _tokenize_modules(src)

    if src.startswith("<layout"):
        root = ET.fromstring(src)
    else:
        root = ET.fromstring(f"<layout>{src}</layout>")

    if root.tag != "layout":
        raise ValueError("root must be <layout>")

    rows = []
    if _norm(root.text):
        raise ValueError("<layout> cannot contain direct text")

    for child in root:
        if child.tag != "row":
            raise ValueError(f"<layout> may contain only <row>, found <{child.tag}>")
        rows.append(_parse_row(child))
        if _norm(child.tail):
            raise ValueError("<layout> cannot contain text between top-level rows")

    return {
        "tree": {
            "type": "layout",
            "attrs": dict(root.attrib),
            "rows": rows,
        },
        "modules": modules,
    }
