from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN = (
    'legacy',
    'compat',
    'fallback',
    'render_target',
    'BUFFER',
    'command_response',
    'response_adapter',
    'state_tree',
)

EXCLUDE_PARTS = {
    'system/library/prompts',
    '.pytest_cache',
    '__pycache__',
}


def _iter_source_files():
    for base in (PROJECT_ROOT / 'system', PROJECT_ROOT / 'extensions', PROJECT_ROOT / 'layout'):
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if not path.is_file():
                continue
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            if any(part in rel for part in EXCLUDE_PARTS):
                continue
            if path.suffix not in {'.py', '.txt', '.json'}:
                continue
            yield path, rel


def test_phase23_repo_uses_canonical_cleanup_vocabulary():
    hits: list[str] = []
    for path, rel in _iter_source_files():
        text = path.read_text(encoding='utf-8', errors='ignore')
        for token in FORBIDDEN:
            if token in text:
                hits.append(f'{rel}: {token}')
    assert hits == []
