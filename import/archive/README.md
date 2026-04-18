# AIGMos

Deterministic command-driven runtime for structured AI, automation, and real-time workflows.

---

## Status

**AIGMos Core 1.0** is the first stable public release of the runtime core.

The command semantics are considered stable. The core execution model — explicit state, commands, triggers, events, runners, and loop-capable execution — has been implemented and validated in real use.

This release is aimed at technical users evaluating the runtime model. It is **not** presented as a polished end-user product.

---

## What this is

AIGMos takes a different approach from chat-first AI tooling.

Instead of centering the system around a conversational interface, AIGMos centers it around a deterministic command surface, explicit state, and inspectable execution.

The goal is to make automation and AI-related workflows:

- structured
- predictable
- inspectable
- composable

---

## Core model

AIGMos is built around three storage primitives and a small set of runtime primitives.

### Storage primitives

- **$** → key/value state
- **&** → ordered lists
- **#** → structured table/tree data

### Runtime primitives

- **!** → triggers
- **@** → events
- **%** → runners / runtime instances

These pieces are designed to work as a single runtime model:

**signals → state → events → execution → actions**

---

## What 1.0 means

Version 1.0 means the core model is stable enough to publish and build against.

It does **not** mean that every future layer already exists.

### Included in 1.0

- stable command semantics
- explicit state model
- deterministic command surface
- triggers
- events
- runners
- loop-capable execution
- persistent state
- import/export path
- terminal-first operation

### Not promised by 1.0

- polished UX
- beginner-friendly onboarding
- large integration catalog
- distributed runtime features
- every possible realtime extension
- every future AI/provider layer

---

## Why this exists

Most AI tooling still tends to be:

- opaque
- hard to audit
- difficult to integrate into strict workflows
- too dependent on hidden assumptions

AIGMos explores a stricter model:

- explicit commands over hidden magic
- explicit state over implicit context
- structured execution over loose prompting
- stable semantics over shifting behavior

---

## High-level comparison

| Typical chat-first tooling | AIGMos |
|---|---|
| chat-centric interaction | command-centric interaction |
| implicit state | explicit state |
| hidden execution | inspectable execution |
| loose workflow boundaries | structured flow boundaries |
| conversational default | operational default |

---

## Who this is for

AIGMos Core 1.0 is primarily relevant for:

- system builders
- automation developers
- CLI-oriented users
- AI infrastructure developers
- people exploring deterministic control surfaces

It is not yet optimized for non-technical users.

---

## Quick example

```text
mk $texts
$texts:title = AIGMos
mk &steps
add &steps "echo hello"
add &steps "echo world"
run &steps
```

A more structured example:

```text
trig !ready $SYSTEM:mode == run
on !ready @start "run %main &boot"
```

---

## Documentation map

- `docs/specs/CANONICAL_SPEC_v1.0.md`
- `docs/specs/COMMANDS.md`
- `docs/specs/RUNTIME.md`
- `docs/specs/IMPORT_EXPORT.md`
- `docs/examples/`

---

## Release framing

This release should be read as:

> **stable public core runtime**
>
> not
>
> **finished mass-market product**

That distinction is intentional.

---

## License

AIGMos uses a Business Source License (BUSL).

See `LICENSE.md` in the repository for the current license text.
