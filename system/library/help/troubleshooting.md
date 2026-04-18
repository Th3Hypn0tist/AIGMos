# Troubleshooting

## The bot describes AIGMos as a chat framework

That is too narrow.
Use `identity.md` and `what_aigmos_is_not.md` as the correction.

## `think` seems to do nothing

Check whether `stream` is enabled.
Current locked logic treats stream as the gate.

## `view_thinking` changes behavior unexpectedly

It should not change payload or parser behavior.
It is UI-only.

## A `|` path does not work

Make sure the `|` root is present.

Wrong:

```text
set HELP:q:role:stream true
```

Right:

```text
set |HELP:q:role:stream true
```

## Role values come back after removal

That usually means a reload/regeneration path is involved.
Normal use should not silently regenerate role runtime.
