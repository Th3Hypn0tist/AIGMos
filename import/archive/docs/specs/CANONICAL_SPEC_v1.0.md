# CANONICAL_SPEC_v1.0

Draft canonical reference for the AIGMos 1.0 release.

This document defines the **core model and semantic freeze** for version 1.0. New features may be added later, but the meaning of the frozen 1.0 primitives and commands should not change incompatibly.

---

## 1. Scope of the 1.0 freeze

The 1.0 freeze covers:

- core storage primitives
- core addressing model
- parser-level command execution assumptions
- command semantics for the stable command surface
- trigger / event / runner runtime semantics
- import / export direction conventions
- persistence expectations for stable runtime objects

The 1.0 freeze does **not** claim:

- complete feature coverage for all future use cases
- every planned realtime extension
- every provider, adapter, or orchestration layer
- polished UX or onboarding

---

## 2. Primitive model

### 2.1 `$` — key/value state

`$` stores symbolic state as key/value pairs.

Examples:

```text
$SYSTEM:mode
$texts:title
$CH:00000
```

Characteristics:

- values are stored as strings
- meaning is resolved by command context
- the namespace is explicit
- keys are addressed with `:`

### 2.2 `&` — ordered lists

`&` stores ordered sequences.

Examples:

```text
&steps:0
&steps:1
&boot:2
```

Characteristics:

- numeric indexing
- append-oriented usage
- suitable for ordered execution and composition

### 2.3 `#` — structured table/tree data

`#` stores structured rows / cells / trees.

Examples:

```text
#jobs:0:cmd
#OSC:in:foo:bar
#codebase:latest:file
```

Characteristics:

- recursive structure
- row / cell style addressing
- suited for structured data and adapter payloads

---

## 3. Runtime object model

### 3.1 `!` — triggers

Triggers evaluate state or time-based conditions and produce runtime signals.

### 3.2 `@` — events

Events bind one trigger to one command.

One event contains one command body.

### 3.3 `%` — runners

Runners represent runtime execution instances, including named and persistent execution flows.

---

## 4. Addressing rules

AIGMos uses prefix-based addressing.

### Valid root spaces

- `$`
- `&`
- `#`
- `!`
- `@`
- `%`

### General rules

- `:` is structural
- names may use dots for readability where allowed
- storage roots and runtime roots are not interchangeable
- command validity depends on target type

Examples:

```text
$SYSTEM:config:layout
&steps:3
#jobs:0:cmd
%main:status
```

---

## 5. Parser assumptions

The parser treats AIGMos as a command surface, not a freeform language.

### Baseline assumptions

- one command is the atomic execution unit
- quoting preserves atomic arguments
- command meaning comes from command definitions, not heuristics
- hidden fallback behavior should be avoided

### Execution sources

A command may be executed directly, or constructed from state/list/table sources depending on the command.

Examples:

```text
run "echo hello"
run $MEM:cmd
run &steps
run #jobs
```

---

## 6. Storage semantics

### 6.1 `$`

- symbolic key/value storage
- explicit key addressing
- no implicit nested object semantics beyond addressing

### 6.2 `&`

- ordered sequence semantics
- insertion is append-style through `add`
- list order is meaningful

### 6.3 `#`

- structured node/row/cell semantics
- recursive tree allowed
- leaf access is different from node access

---

## 7. Command-surface semantic freeze

The following command families are part of the 1.0 stable surface:

- `mk`
- `rm`
- `ls`
- `cat`
- `add`
- `cp`
- `mv`
- `run`
- trigger / event declarations
- import / export commands
- HTTP command family
- `Q` / `Qc` family where enabled in the runtime

The 1.0 promise is semantic stability, not permanent absence of new commands.

---

## 8. Runtime semantics

### 8.1 Trigger semantics

Supported core trigger concepts in 1.0:

- level
- edgeR
- edgeF
- edgeB
- onchange
- cron

A trigger observes conditions and can cause bound events to fire.

### 8.2 Event semantics

- an event reads a trigger
- an event contains exactly one command body
- each firing enqueues work independently
- events are not implicitly deduplicated

### 8.3 Runner semantics

- `%name` identifies a runtime instance
- runner state is exposed through `%name:status`
- named runners persist as runtime objects until removed/stopped
- execution control is explicit

---

## 9. Runner status model

The stable numeric status mapping is:

- `0` = run
- `1` = ok
- `2` = stop
- `3` = error
- `4` = pause

Alias forms may exist, but the semantic model above is the frozen reference.

---

## 10. Persistence expectations

For 1.0, the following are expected to be persistable or restorable as part of the runtime model where supported by the implementation:

- stable state namespaces
- trigger declarations
- event declarations
- runner-relevant state needed for runtime restoration

Exact backend implementation is not part of the semantic contract.

---

## 11. Import / export convention freeze

AIGMos 1.0 uses a consistent direction convention:

```text
<src> <dst>
```

This directionality applies across the copy/move/import/export family unless a command explicitly documents otherwise.

This is part of the 1.0 semantic freeze.

---

## 12. Non-goals for 1.0

The following are intentionally outside the 1.0 promise:

- broad UX polish
- full multi-user governance models
- every advanced realtime feature
- complete distributed execution layer
- complete provider ecosystem
- agent-first abstractions as the primary model

---

## 13. Release definition

AIGMos Core 1.0 should be understood as:

- stable enough to publish
- stable enough to document against
- stable enough to validate with real projects

It should **not** be interpreted as “all future layers are complete.”
