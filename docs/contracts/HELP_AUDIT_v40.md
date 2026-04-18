# Commands help cleanup v40

This pass standardizes `help_short` and `help_full` across the commands tree.

## What was cleaned
- inconsistent or too-thin help text
- explicit legacy marking for non-canonical helpers
- runtime-space restrictions updated to include `|`
- `trig` help aligned with current trigger model
- `run`, `loop`, `new`, import/export and HTTP helper help clarified to describe current implementation truthfully
- `__pycache__` removed from the delivered tree

## Important notes
- Some commands still differ from v40 canonical semantics at implementation level. Their help now states that clearly instead of pretending otherwise.
- Marked as local/legacy helpers in help text: `cycle`, `emit`, `hget`, `hpost`, `import.list`.
