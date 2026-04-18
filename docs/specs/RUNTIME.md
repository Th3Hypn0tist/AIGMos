# RUNTIME

Runtime semantics for AIGMos Core 1.0.

This document describes how triggers, events, runners, and loop-capable execution fit together.

---

## 1. Runtime model

AIGMos treats runtime execution as explicit and inspectable.

The core mental model is:

```text
state -> trigger -> event -> runner / command -> state
```

Nothing important should depend on hidden conversational state.

---

## 2. Triggers (`!`)

Triggers observe conditions and expose a signal-like runtime object.

### Core 1.0 trigger concepts

- `level`
- `edgeR`
- `edgeF`
- `edgeB`
- `onchange`
- `cron`

### Typical declaration

```text
trig !ready $SYSTEM:mode == run
```

### Trigger expression notes

The condition model is intended to stay explicit and composable.

Typical building blocks:

- equality / inequality
- numeric comparisons
- boolean combinations
- time-based schedules for cron-like triggers

### Pulse behavior

Implementations may support pulse windows for trigger flood control. The core design expectation is that trigger activation remains explicit and observable.

---

## 3. Events (`@`)

Events bind a trigger to exactly one command body.

### Typical declaration

```text
on !ready @start "run %main &boot"
```

### Event rules

- one event listens to one trigger
- one event stores one command
- one firing produces one queued unit of work
- events are not implicitly deduplicated

This keeps the runtime model easy to reason about.

---

## 4. Runners (`%`)

Runners are named or unnamed execution instances.

### Why runners exist

Runners provide:

- explicit execution identity
- visible status
- controllable lifecycle
- compatibility with multi-step execution

### Typical examples

```text
run %main &boot
run %worker "echo hello"
```

---

## 5. Runner status model

The stable runner status mapping for 1.0 is:

| Value | Meaning |
|---|---|
| `0` | run |
| `1` | ok |
| `2` | stop |
| `3` | error |
| `4` | pause |

### Example

```text
%main:status = run
%main:status = pause
```

---

## 6. Step-aware execution

Where supported by the runtime, runners expose step-related state such as current step position.

This matters especially for list-driven and loop-driven execution.

Typical examples:

```text
%main:step
%main:status
```

---

## 7. List-driven execution

Lists are natural execution sources.

### Example

```text
mk &boot
add &boot "echo init"
add &boot "echo load"
add &boot "echo done"
run %main &boot
```

A list-driven runner executes the sequence in order.

---

## 8. Table-driven execution

Structured `#` data can also act as an execution source, depending on the runtime composition rules.

### Example idea

```text
#jobs:0:cmd = echo init
#jobs:1:cmd = echo done
run #jobs
```

The runtime composes executable commands from structured rows or cells according to the implementation rules.

---

## 9. Loop-capable execution

AIGMos supports loop-oriented execution patterns built on explicit sources rather than implicit control flow.

The important 1.0 point is not a specific loop syntax, but that loop-capable execution belongs to the stable runtime model.

That means:

- repeated step execution is a first-class runtime concern
- named runtime objects can hold control state
- pause/run/stop behavior remains explicit

---

## 10. Queueing model

Event firings and other runtime actions should enqueue explicit units of work rather than collapse into hidden state transitions.

This matters because it preserves:

- auditability
- predictability
- replayable reasoning
- strict execution boundaries

---

## 11. Persistence and boot expectations

The implementation may restore runtime-relevant declarations and state on boot.

Typical persisted objects include:

- triggers
- events
- stable state namespaces
- configuration relevant to startup behavior

Where autostart exists, startup ordering should remain explicit.

---

## 12. What 1.0 does not require

AIGMos Core 1.0 does **not** require every advanced runtime feature that could exist later.

For example, later additions may include:

- richer realtime trigger operators
- expanded scheduler behavior
- broader distributed execution control
- more elaborate runtime inspection tools

Those can arrive later without invalidating the 1.0 runtime model.
