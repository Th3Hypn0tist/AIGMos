# Layouts and Instances

## What `|` means

`|` is the root for a layout instance and its instance-owned runtime data.

## Creation form

```text
new |HELP /help
new |Q /q
new |MON /qmon
```

## Important rule

The layout instance name is the runtime identity.
The template title is only display metadata.

## Typical instance data

```text
|HELP:meta:title
|HELP:meta:active_module
|HELP:buffer
|HELP:command_history
|HELP:q:...
```

## Persistence rule

`|` is the source of truth for layout instances.
A parallel `#SYSTEM:runtime:layouts` snapshot is not the target model.

## What layouts are for

Layouts provide operator-facing views and input routing.
They are not the whole system.

## Chat relation

A layout may host `q`, `monitor`, `label`, `cs`, and other modules.
That does not make the whole runtime a chat framework.
