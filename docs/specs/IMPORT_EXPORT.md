# IMPORT_EXPORT

Import and export reference for AIGMos Core 1.0.

This document focuses on the direction conventions and practical expectations for file/code import and export commands.

---

## 1. Direction rule

The stable convention is:

```text
<src> <dst>
```

This rule should remain consistent across:

- `cp`
- `mv`
- `import.*`
- `export.*`

This is one of the important semantic consistency rules in the 1.0 surface.

---

## 2. `import.file`

Import a file into an AIGMos target.

### Syntax

```text
import.file <src> <dst>
```

### Example

```text
import.file ./note.txt $texts:note
```

### Typical use

- plain text into `$`
- file content into a structured or state target
- external material into the command surface

---

## 3. `import.code`

Import code or command-like text into an execution-oriented target.

### Syntax

```text
import.code <src> <dst>
```

### Examples

```text
import.code ./steps.txt &boot
import.code ./job.txt $MEM:cmd
```

### Typical use

- load command sequences
- seed runnable content from files
- prepare execution inputs externally

---

## 4. `export.file`

Export AIGMos content to a file.

### Syntax

```text
export.file <src> <dst>
```

### Example

```text
export.file $texts:note ./note.txt
```

### Typical use

- write state back to disk
- externalize generated content
- produce reviewable outputs

---

## 5. `export.code`

Export command/code-oriented content to a file.

### Syntax

```text
export.code <src> <dst>
```

### Example

```text
export.code &boot ./boot.txt
```

---

## 6. Consistency requirement

A common source of confusion in command surfaces is inconsistent argument order.

AIGMos 1.0 intentionally standardizes these families around:

```text
source first
destination second
```

That consistency is part of the point.

---

## 7. Practical guidance

### Use `$` when:

- importing or exporting a single text-like value
- moving content in and out of symbolic state

### Use `&` when:

- importing or exporting ordered command sequences
- preserving step order matters

### Use `#` when:

- importing or exporting structured payloads
- the target is tree/table-shaped

---

## 8. Release note relevance

If import/export direction or route handling was one of the last meaningful fixes before release, that is usually a good sign:

- the core model already held
- remaining issues were in the boundary path
- release work shifts from invention to packaging

That is the right kind of late-stage fix for a 1.0 release.
