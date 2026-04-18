# 01_quickstart

Minimal current-snapshot terminal-first example.

```text
mk $texts
set $texts:title AIGMos

mk &steps
add &steps "echo hello"
add &steps "echo world"

ls $
cat $texts:title
run &steps
```

Layout-oriented quick start:

```text
new |CS /cs
new |Q /q
new |HELP /help
```

What this shows:

- create state
- append ordered steps
- inspect state
- execute a routine
- create layout instances for normal work and help
