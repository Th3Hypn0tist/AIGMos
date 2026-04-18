# Command surface

This is a practical current-snapshot command guide.

It does not try to freeze future semantics. It describes the command surface that exists in the current repository.

---

## State and inspection

### `mk`

```text
mk <target>
```

Create an empty state node.

Examples:

```text
mk $texts
mk &steps
mk #jobs
```

### `set`

```text
set <symbol> <value>
```

Write one value to one symbol.

### `ls`

```text
ls [target|prefix*]
```

List roots, direct children, wildcard matches, or selected runtime objects.

### `cat`

```text
cat <target>
```

Show one resolved target in readable form.

---

## Structural edits

### `add`

```text
add <target> <source>
```

Append one value to `$`, `#`, or `&` target according to target rules.

### `cp`

```text
cp <src> <dst>
```

Copy one state-side symbol or subtree.

### `mv`

```text
mv <src> <dst>
```

Move one state-side symbol or subtree.

### `rm`

```text
rm <target>
```

Remove one state symbol, subtree, or runtime object.

---

## Runners, triggers, and events

### `run`

```text
run <command|&source>
```

Current implementation runs one direct command or one indexed `&` routine once.

### `loop`

```text
loop &name
```

Current implementation creates a `%name` loop-mode runner from an indexed source.

### `cycle`

```text
cycle <source>
```

Helper command for cycle-mode runner creation.

### `trig`

```text
trig !name <expr>
trig !name onchange <ref>
trig !name cron "spec"
```

Create a trigger.

### `on`

```text
on !trigger @event "command"
```

Bind one trigger to one named event and one quoted command payload.

### `emit`

```text
emit @event
emit !trigger
```

Helper command to emit one event or push one trigger into the trigger bus.

---

## Import, export, and mapping

### `import.file`

```text
import.file <src> <target>
```

### `import.json`

```text
import.json <input> <output>
```

### `import.code`

```text
import.code <src> <dst>
```

### `import.list`

```text
import.list <source> <target>
```

Helper command for list-like imports.

### `export.file`

```text
export.file <src> <dst>
```

### `export.json`

```text
export.json <src> <dst>
```

### `export.code`

```text
export.code <src> <dst>
```

### `map.structure`

```text
map.structure #input [$output]
```

### `map.files`

```text
map.files #input [$output]
```

---

## q / qc

### `q`

```text
q[.profile] <prompt...>
```

Stateful chat command.

### `qc`

```text
qc[.profile] <output> <prompt...>
```

Stateless structured q call with explicit output target.

See `Q_AND_QC.md` for details.

---

## Layout and UI

### `new`

```text
new |<instance> /<module-or-layout>
```

Create one layout module instance or bind one layout definition.

Examples:

```text
new |CS /cs
new |Q /q
new |HELP /help
new |LLAMA /q.qwen
```

### `bind`

```text
bind alt-1..alt-9|alt-0 <command...>
```

### `unbind`

```text
unbind alt-1..alt-9|alt-0
```

### `binds`

```text
binds
```

List current hotkey bindings.

---

## HTTP helpers

### `hget`

```text
hget <output> <url|symbol>
```

### `hpost`

```text
hpost <output> <url|symbol> <raw-body...>
```

---

## Utility commands

### `echo`

```text
echo <message>
```

### `get`

```text
get <output> <symbol>
```

---

## Slash commands

Main slash surface:

```text
/help [/cmd]
/time
/greeting
/clear
/reload [...]
/health q[.alias]
/exit
```

Important current slash routes:

```text
/cs
/q
/monitor[.alias]
```

---

## Notes

- Current command names in code are lowercase: `q`, `qc`, `new`, `run`, `loop`, and so on.
- Some older spec files still show earlier forms or capitalization.
- For the current repository snapshot, follow the command implementations in `system/cs/commands/`.
