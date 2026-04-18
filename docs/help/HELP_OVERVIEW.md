# Help overview

This folder exists to support two audiences:

1. operators using the current AIGMos runtime
2. builders creating help-oriented layouts such as `|HELP`

The goal is simple: when someone opens a help layout or asks how the current snapshot works, there should be one clear place to start.

---

## What help currently means in AIGMos

In the current repository, help is not a separate product layer.

It is a combination of:

- documentation files
- the `/help` slash command surface
- the `help.tmpl` layout definition
- normal `q` behavior inside a help-oriented layout

Typical creation:

```text
new |HELP /help
```

That creates a bound layout instance named `|HELP` using `system/library/layout/help.tmpl`.

---

## Current help-related files

Repository docs:

- `docs/help/HELP_OVERVIEW.md`
- `docs/help/COMMAND_SURFACE.md`
- `docs/help/LAYOUTS_AND_HELP.md`
- `docs/help/Q_AND_QC.md`
- `docs/help/TROUBLESHOOTING.md`

Runtime-side help assets:

- `system/library/layout/help.tmpl`
- `system/library/help/index.md`
- `system/library/help/current_snapshot.md`
- `system/library/prompts/explanations/help`

---

## Fast operator workflow

Basic session:

```text
new |CS /cs
new |Q /q
new |HELP /help
```

Typical checks:

```text
/help
/help q
/help new
binds
ls $
ls |
```

---

## Important current rules

- `|instance` is the runtime identity
- `<layout title="...">` provides a default display title
- `q` and `qc` are lowercase in the current code
- `new` uses `new |<instance> /<module-or-layout>`
- help should explain the current code snapshot, not only older canonical docs

---

## Read next

- `COMMAND_SURFACE.md` for command-level help
- `LAYOUTS_AND_HELP.md` for layout/help-instance behavior
- `Q_AND_QC.md` for AI/chat behavior
- `TROUBLESHOOTING.md` for common failure modes
