# Editor Save Ownership v1

Status: canonical lock
Scope: `system/layout/modules/editor.py`

## Purpose

Lock the ownership boundary for editor-originated writes.

## Ownership

- **Editor instance** owns only:
  - writes to the edited target symbol
  - editor-local metadata needed for save/error status
- **Renderer** does not own save behavior
- **Layout registry/state** may provide instance metadata, but the save operation itself remains editor-owned

## Writer Tag Rule

Editor-originated writes must use:

```txt
editor:<handle>
```

Examples:

```txt
editor:EDITOR
editor:EDITOR.2
```

## Allowed Write Scope

Editor may write only to:

- the symbol currently under edit
- editor-local save metadata such as last-save status and timestamps

## Forbidden

Editor may not:

- mutate unrelated business state
- write with generic tags such as `editor` or `layout`
- hide writes behind renderer behavior

## Save Path Rule

The editor save path is responsible for:

1. parsing the current editor buffer into the configured output form
2. writing the target symbol through the normal state API
3. preserving editor ownership via `editor:<handle>`

## Branch Clear Rule

When the editor clears a `#` subtree before rewriting it, the clear operation must remain editor-owned.

Allowed form:

```txt
remove_subtree(..., writer=editor:<handle>, op=editor_branch_clear)
```

## Durable vs Live

- live typed content may exist in the editor instance/render target
- durable saved truth exists in the target symbol after a successful save

## Acceptance

The editor save path is considered correct when:

- saved target writes are attributable to `editor:<handle>`
- subtree clear before branch rewrite is attributable to `editor:<handle>`
- editor does not mutate unrelated state
- renderer remains read-only
