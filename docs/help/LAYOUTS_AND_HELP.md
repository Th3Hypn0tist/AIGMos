# Layouts and help

This document explains the current layout model and how the help layout fits into it.

---

## Core rule

A layout instance is identified by its `|handle`.

Examples:

```text
|CS
|Q
|HELP
|Q.llama
|BUFFER.log
```

That handle is the runtime identity.

It is not the same thing as the template file name.

---

## Creation

Create layouts with:

```text
new |<instance> /<module-or-layout>
```

Examples:

```text
new |CS /cs
new |Q /q
new |HELP /help
new |QMON /qmon
```

---

## Current shipped layout files

Under `system/library/layout/` the current repository ships these templates:

- `cs.tmpl`
- `q.tmpl`
- `qcs.tmpl`
- `qmon.tmpl`
- `help.tmpl`
- `xx.tmpl`

Not all of them are equally “clean” examples.

A good practical baseline is:

- `cs.tmpl` for command-surface/basic monitor usage
- `q.tmpl` for a normal q layout
- `help.tmpl` for help-oriented usage
- `qmon.tmpl` for q-state monitoring

`qcs.tmpl` and `xx.tmpl` are more demo-like and may contain explicit alias references.

---

## Current help layout

The help layout is defined in:

```text
system/library/layout/help.tmpl
```

Current intent:

- top label shows the instance title
- q view provides help-oriented interaction
- cs input gives direct command access

Typical usage:

```text
new |HELP /help
```

---

## Important current DSL rules

### `<layout title="...">`

This is the default display title.

### `<layout name="...">`

Treat this as invalid / ignored for runtime identity.

### `|:title`

Used inside labels to read the instance display title.

Example:

```text
<label input="|:title">
```

---

## Main built-in modules

### `<cs>`

Command-surface module.

### `<monitor>`

General monitor for normal target/buffer viewing.

### `<q>`

q-oriented module that shows q state owned by its target instance.

### `<qmon>`

Read-only q monitor. Useful when you want to inspect another q instance without creating another q owner.

Example idea:

```text
<qmon alias="|Q">
```

This should monitor the q state of `|Q`.

---

## Help-oriented recommended setup

Minimal:

```text
new |HELP /help
```

More explicit working set:

```text
new |CS /cs
new |Q /q
new |HELP /help
new |QMON /qmon
```

That gives:

- one general command surface
- one q workspace
- one help workspace
- one monitor workspace

---

## Safety rule

Invalid layout switches should be handled as normal errors.

They should not crash the curses UI loop.

Example failure case:

```text
|Q
```

when `|Q` does not exist yet.

Expected behavior:

```text
[error] Invalid layout
```

---

## Reload note

`/reload layout` is expected to rebuild layout state from current template/module definitions.

If a layout change does not appear after reload, verify that:

- the correct `.tmpl` file changed
- the target layout instance actually uses that route
- the current runtime snapshot rebuilt successfully
