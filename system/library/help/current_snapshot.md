# Current Snapshot

## Current orientation

- `|` is the runtime identity for layout instances
- `|` stays its own symbol space
- `|` is the source of truth for layout instance state
- `#SYSTEM:runtime:layouts` is no longer the architectural target
- `q` and `qc` are lowercase
- `new |<instance> /<layout-or-module>` is the creation form
- `.tmpl` files define layouts
- `system/lib/q/qview.py` is the canonical qview source

## Locked q logic

```text
stream = gate
think = payload-intent
view_thinking = UI-only
```

### Resulting rules

- `stream = true` enables stream transport mode
- `stream = false` disables stream transport mode
- `think = true` merges `think_payload`
- `think = false` merges `nothink_payload`
- `view_thinking = true` shows actual thinking text
- `view_thinking = false` never changes payload or parser behavior

## Minimum live feedback rule

During a running answer, show at least:

```text
[Thinking...]
```

## Role/runtime rule

- normal use must not regenerate role runtime unexpectedly
- reload is the regeneration path

## Canonical qview rule

Only one qview implementation should own the real logic.
Other qview entry points should be wrappers or imports to the canonical file.
