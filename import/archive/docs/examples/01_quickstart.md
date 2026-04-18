# 01_quickstart

Minimal terminal-first example.

```text
mk $texts
$texts:title = AIGMos

mk &steps
add &steps "echo hello"
add &steps "echo world"

ls $
cat $texts:title
run &steps
```

What this shows:

- create state
- create a list
- append steps
- inspect state
- execute a list
