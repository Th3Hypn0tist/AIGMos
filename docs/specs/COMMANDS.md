# COMMANDS

Stable command-surface reference for AIGMos Core 1.0.

This document focuses on the stable semantics of the main commands. Examples are intentionally small and terminal-first.

---

## 1. `mk`

Create or initialize a target namespace / structure.

### Syntax

```text
mk <target>
```

### Valid targets

- `$...`
- `&...`
- `#...`

### Examples

```text
mk $texts
mk &steps
mk #jobs
```

---

## 2. `rm`

Remove a target.

### Syntax

```text
rm <target>
```

### Notes

- applies to storage targets
- applies to runtime targets when removal/stop semantics are defined
- `rm %name` removes/stops the runner instance
- `rm !name` removes the trigger declaration
- `rm @name` removes the event declaration

### Examples

```text
rm $texts:title
rm &steps:0
rm #jobs:0:cmd
rm %main
rm !ready
rm @start
```

---

## 3. `ls`

List the immediate contents of a target.

### Syntax

```text
ls <target>
```

### Notes

- intended for inspection
- not a recursive dump
- output depends on target type

### Examples

```text
ls $
ls $SYSTEM
ls &steps
ls #jobs
ls !
ls @
```

---

## 4. `cat`

Read the concrete value of a value-like target.

### Syntax

```text
cat <target>
```

### Notes

- valid for `$` keys
- valid for `&` indexes
- valid for `#` leaves
- reading a large structural node as a single leaf is not the intended mode
- leaf/value access is stricter than list/structure inspection

### Examples

```text
cat $texts:title
cat &steps:0
cat #jobs:0:cmd
```

---

## 5. `add`

Append or insert according to the target collection rules.

### Syntax

```text
add <target> <value>
```

### Applies to

- `$`
- `&`
- `#`

### Semantics

#### `&`

Appends directly to the next list index.

#### `$`

Finds the highest numeric child key under the target and inserts at the next integer key.

If any non-numeric child key exists under that target, `add` must error.

#### `#`

Finds the highest numeric child key under the target and inserts at the next integer key.

If any non-numeric child key exists under that target in the relevant insertion context, `add` must error.

### Examples

```text
add &steps "echo hello"
add $CH "user message"
add #rows "value"
```

---

## 6. `cp`

Copy from source to destination.

### Syntax

```text
cp <src> <dst>
```

### Notes

- follows the global direction convention: source first, destination second
- may perform normalization when crossing between storage types
- does **not** apply to runtime spaces `%`, `!`, `@`

### Examples

```text
cp $texts:title $backup:title
cp &steps:0 #jobs:0:cmd
cp #jobs:0:cmd $MEM:last_cmd
```

---

## 7. `mv`

Move/rename from source to destination.

### Syntax

```text
mv <src> <dst>
```

### Notes

- follows the global direction convention: source first, destination second
- used for structural moves / renames in supported spaces
- does **not** apply to runtime spaces `%`, `!`, `@`

### Examples

```text
mv $texts:title $texts:name
mv #jobs:0:cmd #jobs:0:command
```

---

## 8. `run`

Execute a command source.

### Syntax

```text
run <source>
```

### Supported forms

```text
run "single command"
run $namespace:key
run &list
run #table
run %name "single command"
run %name &list
```

### Notes

- execution is explicit
- named runners expose runtime state through `%name:*`
- list and table execution follow their own composition rules

### Examples

```text
run "echo hello"
run $MEM:cmd
run &steps
run #jobs
run %main &boot
```

---

## 9. Trigger declaration

Create a trigger.

### Syntax

```text
trig !<name> <expression>
```

### Example

```text
trig !ready $SYSTEM:mode == run
```

### Notes

- the exact trigger type may be defaulted or specified by the runtime
- level-based triggering is the common baseline
- additional core types are documented in `RUNTIME.md`

---

## 10. Event declaration

Bind a trigger to one command.

### Syntax

```text
on !<trigger> @<event_name> "<command>"
```

### Example

```text
on !ready @start "run %main &boot"
```

### Notes

- one event = one command body
- the command is stored as-is
- event firings enqueue work independently

---

## 11. `Q` and `Qc`

LLM-facing command family, where enabled.

### Typical roles

- `Q` → chat/history-oriented interaction
- `Qc` → single-shot structured request/response usage

### Example

```text
Qc my.alias "Summarize this" $MEM:result
```

Implementation details may vary by adapter, but the command family belongs to the documented surface where present.

---

## 12. HTTP command family

Stateless outbound HTTP operations.

### Typical forms

```text
HTTP.GET <url> <output>
HTTP.POST <url> <body> <output>
HTTP.PUT <url> <body> <output>
HTTP.DELETE <url> <output>
HTTP.PATCH <url> <body> <output>
HTTP.HEAD <url> <output>
```

### Notes

- output target is typically a `#` path
- body is explicit where applicable
- no hidden session semantics assumed by default

---

## 13. Import / export family

See `IMPORT_EXPORT.md` for the full direction and usage notes.

Core rule:

```text
<src> <dst>
```

Examples:

```text
import.file ./note.txt $texts:note
import.code ./ops.txt &steps
export.file $texts:note ./note.txt
```

---

## 14. Slash commands and UI helpers

Terminal convenience commands may exist in the implementation, but they are not the main semantic center of the 1.0 runtime model.

The 1.0 core should be explained primarily through the command surface above.
