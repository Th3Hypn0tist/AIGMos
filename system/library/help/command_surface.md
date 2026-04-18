# Command Surface

## Core idea

The command surface is the single explicit control surface for the system.

## Parser view

A line becomes one of:

1. event declaration
2. assignment
3. command

## Why it matters

The command surface is the choke point for explicit mutation and execution.

## Built-in command families in the current snapshot

```text
/
add
bind
binds
cat
cp
cycle
echo
emit
export.code
export.file
export.json
get
hget
hpost
import.code
import.file
import.json
import.list
loop
ls
map.files
map.structure
mk
mv
new
on
q
qc
reload
rm
run
set
trig
unbind
```

## Main command groups

### State and structure

- `mk`
- `set`
- `get`
- `ls`
- `cat`
- `rm`
- `cp`
- `mv`
- `add`

### Import / export / mapping

- `import.file`
- `import.json`
- `import.code`
- `import.list`
- `export.file`
- `export.json`
- `export.code`
- `map.files`
- `map.structure`

### Layout and runtime

- `new`
- `bind`
- `binds`
- `unbind`
- `run`
- `loop`
- `cycle`
- `emit`
- `trig`
- `on`

### AI

- `q`
- `qc`
- `/q[.<alias>]`

## Slash surface

Examples:

```text
/help
/help ls
/reload all
/clear
/time
```
