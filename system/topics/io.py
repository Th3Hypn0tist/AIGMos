# system/topics/io.py
#
# POC-MVP IO boundary (no hardening yet)
#
# Commands (aliases expected):
#   import.file <src_file> <dst>           dst: $sub:key OR #a:b:c
#   import.many <src_dir>  <dst_root>      dst_root: #a:b:c   (dict root)
#   export.file <src> [dst_file]           src: $sub:key OR #a:b:c
#   export.many <src_root> [dst_dir]       src_root: #a:b:c   (dict root)
#
# Defaults:
#   export.file dst default: ./output/<auto>.txt
#   export.many dst default: ./output/<auto_dir>/

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from system.lib import tables as tbl

TEXTS_ROOT = "texts"
TABLES_ROOT = "tables"


def _parse_hash(tok: str) -> List[str]:
    if not (isinstance(tok, str) and tok.startswith("#") and len(tok) > 1):
        raise ValueError("Expected #<path>")
    parts = tok[1:].split(":")
    if any(p == "" for p in parts):
        raise ValueError("Invalid # path")
    return parts


def _split_kv(tok: str) -> Tuple[str, str]:
    if not (isinstance(tok, str) and tok.startswith("$") and len(tok) > 1):
        raise ValueError("Expected $<sub>:<key>")
    body = tok[1:]
    if ":" not in body:
        raise ValueError("Expected $<sub>:<key>")
    sub, key = body.split(":", 1)
    if not sub or not key:
        raise ValueError("Expected $<sub>:<key>")
    return sub, key


def _auto_file_name(src: str) -> str:
    # $sub:key -> sub__key.txt
    # #a:b:c   -> a__b__c.txt
    body = src[1:] if src and src[0] in ("$", "#") else src
    safe = body.replace(":", "__")
    return f"{safe}.txt"


def _auto_dir_name(src_root: str) -> str:
    body = src_root[1:] if src_root.startswith("#") else src_root
    return body.replace(":", "__")


def _ensure_output_dir():
    Path("./output").mkdir(parents=True, exist_ok=True)


def _atomic_write_text(dst: Path, text: str):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(dst)


@dataclass
class _IgnoreRule:
    base_dir: Path          # directory containing the .ignore file
    pattern: str            # pattern as written (trimmed/unescaped)
    negated: bool           # True if starts with '!'
    dir_only: bool          # True if endswith '/'
    anchored: bool          # True if startswith '/'
    regex: re.Pattern       # compiled matcher against posix rel path


def _read_utf8_strict(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"UTF-8 decode error in file: {p} (abs={p.resolve()}) :: {e}") from e


def _gitignore_unescape(s: str) -> str:
    # Minimal gitignore-style unescape for leading escape sequences.
    # Handles: \#, \!, \ , \\
    out = []
    esc = False
    for ch in s:
        if esc:
            out.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
        else:
            out.append(ch)
    if esc:
        out.append("\\")
    return "".join(out)


def _gitignore_line_parse(line: str):
    # Returns (negated, pattern_raw) or None
    # Strip newline; keep internal spaces; remove trailing spaces unless escaped.
    s = line.rstrip("\n")
    if not s:
        return None
    # comment if first non-escaped char is '#'
    if s.startswith("#"):
        return None

    # handle trailing spaces (gitignore: trailing spaces ignored unless escaped)
    # MVP: trim right spaces if not escaped
    if s.endswith(" ") and not s.endswith("\ "):
        s = s.rstrip(" ")

    neg = False
    if s.startswith("!"):
        neg = True
        s = s[1:]
    s = _gitignore_unescape(s)
    if not s:
        return None
    return neg, s


def _gitignore_pattern_to_regex(pat: str):
    # Convert gitignore glob to regex.
    # Rules:
    # - '*'  => [^/]* (does not cross '/')
    # - '?'  => [^/]
    # - '**' => .*    (can cross '/')
    # - character classes [] as in fnmatch (keep semantics; avoid matching '/')
    i = 0
    res = ""
    n = len(pat)
    while i < n:
        c = pat[i]
        if c == "*":
            if i + 1 < n and pat[i + 1] == "*":
                # consume consecutive ** (treat as .*)
                while i + 1 < n and pat[i + 1] == "*":
                    i += 1
                res += ".*"
            else:
                res += "[^/]*"
        elif c == "?":
            res += "[^/]"
        elif c == "[":
            j = i + 1
            if j < n and pat[j] in ("!", "^"):
                j += 1
            if j < n and pat[j] == "]":
                j += 1
            while j < n and pat[j] != "]":
                j += 1
            if j >= n:
                res += re.escape(c)
            else:
                stuff = pat[i + 1 : j]
                # translate leading ! to ^ for regex
                if stuff.startswith("!"):
                    stuff = "^" + stuff[1:]
                # do not allow '/' in class
                stuff = stuff.replace("/", "")
                res += "[" + stuff + "]"
                i = j
        else:
            res += re.escape(c)
        i += 1
    return res


def _compile_ignore_rule(base_dir: Path, negated: bool, raw_pat: str) -> _IgnoreRule:
    anchored = raw_pat.startswith("/")
    pat = raw_pat[1:] if anchored else raw_pat

    dir_only = pat.endswith("/")
    if dir_only:
        pat = pat[:-1]

    # If pattern contains no '/', it matches in any directory (like **/pat)
    if "/" not in pat:
        pat = "**/" + pat

    # Build regex anchored to full relative path
    rx = _gitignore_pattern_to_regex(pat)
    regex = re.compile(r"^" + rx + r"($|/.*$)") if dir_only else re.compile(r"^" + rx + r"$")
    return _IgnoreRule(
        base_dir=base_dir,
        pattern=raw_pat,
        negated=negated,
        dir_only=dir_only,
        anchored=anchored,
        regex=regex,
    )


def _load_ignore_rules(dir_path: Path):
    p = dir_path / ".ignore"
    if not p.exists() or not p.is_file():
        return []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        # If .ignore itself isn't UTF-8, ignore it for POC-MVP (and keep importing)
        return []
    rules = []
    for line in lines:
        parsed = _gitignore_line_parse(line)
        if not parsed:
            continue
        neg, pat = parsed
        rules.append(_compile_ignore_rule(dir_path, neg, pat))
    return rules


def _is_ignored(path_abs: Path, is_dir: bool, rules_stack):
    # Gitignore-equivalent: last match wins (across stacked .ignore files)
    # Candidate path is tested as rel path from each rule.base_dir (if applicable).
    decision = None  # None=not matched yet, True=ignored, False=included
    for rule in rules_stack:
        try:
            rel = path_abs.relative_to(rule.base_dir).as_posix()
        except Exception:
            continue
        if rel == ".":
            continue
        if rule.dir_only and not is_dir:
            # dir-only rule doesn't match files directly
            continue
        if rule.regex.match(rel):
            decision = (not rule.negated)
    return bool(decision) if decision is not None else False



def import_file(core, src_file: str, dst: str):
    p = Path(src_file)
    if not p.is_file():
        raise ValueError("import.file expects a readable file path")

    text = _read_utf8_strict(p)

    if dst.startswith("$"):
        sub, key = _split_kv(dst)
        core.kvl[TEXTS_ROOT].setdefault(sub, {})
        core.kvl[TEXTS_ROOT][sub][key] = text
        return "OK"

    if dst.startswith("#"):
        path = _parse_hash(dst)
        tbl.leaf_set(core.tables, TABLES_ROOT, path, text)
        return "OK"

    raise ValueError("import.file dst must be $sub:key or #path")


def import_many(core, src_dir: str, dst_root: str):
    p = Path(src_dir)
    if not p.is_dir():
        raise ValueError("import.many expects a directory path")

    if not dst_root.startswith("#"):
        raise ValueError("import.many dst must be #path root")

    root_path = _parse_hash(dst_root)

    # ensure root dict exists
    tbl.node_ensure_dict(core.tables, TABLES_ROOT, root_path)

    imported = 0
    skipped_ignore = 0
    skipped_binary = 0
    skipped_other = 0

    def walk_dir(dir_abs: Path, rules_stack):
        nonlocal imported, skipped_ignore, skipped_binary, skipped_other

        # load .ignore here (gitignore-equivalent cascading)
        local_rules = _load_ignore_rules(dir_abs)
        if local_rules:
            rules_stack = rules_stack + local_rules

        # deterministic traversal
        try:
            entries = sorted(dir_abs.iterdir(), key=lambda x: x.name)
        except Exception:
            return

        for e in entries:
            try:
                is_dir = e.is_dir()
                is_file = e.is_file()
            except Exception:
                skipped_other += 1
                continue

            if _is_ignored(e, is_dir=is_dir, rules_stack=rules_stack):
                skipped_ignore += 1
                # git behavior: do not traverse ignored dirs
                continue

            if is_dir:
                walk_dir(e, rules_stack)
                continue

            if not is_file:
                continue

            # store path tokens under dst_root
            try:
                rel = e.relative_to(p)
            except Exception:
                continue
            rel_tokens = list(rel.parts)

            try:
                txt = _read_utf8_strict(e)
            except ValueError:
                skipped_binary += 1
                continue
            except Exception:
                skipped_other += 1
                continue

            tbl.leaf_set(core.tables, TABLES_ROOT, root_path + rel_tokens, txt)
            imported += 1

    walk_dir(p, [])

    return f"OK imported={imported} skipped_ignore={skipped_ignore} skipped_binary={skipped_binary} skipped_other={skipped_other}"




def export_file(core, src: str, dst_file: str = None):
    if src.startswith("$"):
        sub, key = _split_kv(src)
        core._require_kv_sub(TEXTS_ROOT, sub)
        if key not in core.kvl[TEXTS_ROOT][sub]:
            raise ValueError("Key not found")
        text = str(core.kvl[TEXTS_ROOT][sub][key])
    elif src.startswith("#"):
        path = _parse_hash(src)
        node = tbl.node_get(core.tables, TABLES_ROOT, path)
        if node is None:
            raise ValueError("Source #path not found")
        if isinstance(node, dict):
            raise ValueError("export.file expects a leaf; use export.many for trees")
        text = str(node)
    else:
        raise ValueError("export.file src must be $sub:key or #path")

    if not dst_file:
        _ensure_output_dir()
        dst = Path("./output") / _auto_file_name(src)
    else:
        dst = Path(dst_file)

    _atomic_write_text(dst, text)
    return str(dst)


def export_many(core, src_root: str, dst_dir: str = None):
    if not src_root.startswith("#"):
        raise ValueError("export.many src must be #path root")

    root_tokens = _parse_hash(src_root)
    node = tbl.node_get(core.tables, TABLES_ROOT, root_tokens)
    if node is None:
        raise ValueError("Source #root not found")
    if not isinstance(node, dict):
        raise ValueError("export.many expects a dict root")

    if not dst_dir:
        _ensure_output_dir()
        dst_root = Path("./output") / _auto_dir_name(src_root)
    else:
        dst_root = Path(dst_dir)

    dst_root.mkdir(parents=True, exist_ok=True)

    # write all leaves under subtree
    leaves = tbl.walk_leaves(core.tables, TABLES_ROOT, root_tokens)
    for path_tokens, text in leaves:
        rel_tokens = path_tokens[len(root_tokens):]
        if not rel_tokens:
            continue
        out_path = dst_root.joinpath(*rel_tokens)
        _atomic_write_text(out_path, text)

    return str(dst_root)


COMMANDS = {
    "sys.io.import.file": (import_file, "Import one OS file into $ or #", "import.file <src_file> <$sub:key|#path>"),
    "sys.io.import.many": (import_many, "Import OS directory tree into #", "import.many <src_dir> #path"),
    "sys.io.export.file": (export_file, "Export one $/# leaf to OS file", "export.file <$sub:key|#path> [dst_file]"),
    "sys.io.export.many": (export_many, "Export one # tree to OS directory", "export.many #path [dst_dir]"),
}
