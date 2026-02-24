# AIGMos

Deterministic AI governance console and structured runtime.

Status: Architecture Alpha (Stage1)

---

Status: Architecture Alpha (Stage1)

## Core Concept: Symbolic Memory

AIGMos is designed to operate with a structured memory model rather than relying on opaque conversational context.

The foundational approach is described in the related project:

JIT Symbolic Memory  
https://github.com/Th3Hypn0tist/jit-symbolic-memory

This model introduces:

- Explicit, inspectable memory structures
- Separation between runtime execution and persistent symbolic state
- Deterministic memory access instead of hidden context windows

In the AIGMos architecture, LLM interaction is intended to operate on top of this symbolic memory layer rather than replacing it.

## What this is

This project explores a different approach to AI systems:

Instead of treating AI as a black-box chat interface, this system provides a **deterministic command surface**, explicit state control, and auditable execution flow.

The goal is to make AI interaction:
- structured
- predictable
- inspectable
- composable

This repository represents the **first public footprint** of the architecture.

---

## Why this exists

Current AI tooling is mostly:

- opaque
- non-deterministic
- difficult to audit
- hard to integrate into structured workflows

This project investigates an alternative paradigm:

> AI as a **governed runtime**, not a conversational endpoint.

Key design principles:

- explicit commands over hidden magic
- deterministic state transitions
- clear separation of structure vs execution
- modular, inspectable system layers

---

## Current Status

**Development stage:** Architecture Alpha (Stage1)

This means:

- Core primitives are implemented
- System is operational
- Architecture is considered stable
- Many features are intentionally unfinished

This is **not** a production system and is not yet intended for general users.

---

## What currently works

Core system capabilities include:

- Deterministic command surface
- Structured namespace model
- List and routine primitives
- Execution pipeline ("runner")
- Persistent system state
- Terminal UI environment

The focus at this stage is validating the architecture, not feature completeness.

---

## What is NOT ready

The following areas are intentionally incomplete:

- Polished UX
- Comprehensive documentation
- Installation automation
- Advanced integrations
- Performance optimization
- Production-level stability guarantees

Future layers (not yet included):

- LLM orchestration
- Agent frameworks
- Distributed execution
- Advanced symbolic memory systems

---

## Project Philosophy

This project is based on a core idea:

> AI systems should be **governable infrastructure**, not unpredictable assistants.

This leads to a different design approach:

| Traditional AI | This System |
|----------------|-------------|
| Chat-centric | Command-centric |
| Implicit state | Explicit state |
| Hidden execution | Inspectable execution |
| Black-box behavior | Deterministic flow |

---

## Who this is for (at this stage)

The current alpha phase is mainly relevant for:

- system architects
- AI infrastructure developers
- CLI power users
- researchers exploring structured AI interaction models

It is not yet intended for non-technical users.

---

## What it can do today

AIGMos is not an AI agent system.

It is a deterministic command runtime that can execute structured tasks, including controlled interaction with a single LLM.

In practice this means:

- Commands can be defined and executed through a predictable runtime pipeline
- The system maintains explicit state instead of relying on hidden conversational context
- Every execution step is inspectable and reproducible
- A single LLM call can already be executed as part of a controlled command flow

For example:

Instead of sending prompts directly to an LLM, AIGMos treats an LLM call as just another runtime action:

command >> runtime pipeline >> LLM call >> stored output >> inspectable history

The system does NOT yet implement:

- multi-LLM routing
- agent autonomy
- workflow orchestration
- automatic reasoning chains

Those are considered future layers.

---

## Alpha Testing

This repository marks the start of a closed alpha phase.

Feedback is welcome especially on:

- architectural clarity
- command surface design
- usability of deterministic workflows
- conceptual alignment with real-world AI governance needs

This phase prioritizes **observational feedback**, not feature requests.

---

## Repository Structure (high-level)

```
/core           → system primitives and runtime logic
/ui             → terminal interface components
/modules        → extension system (experimental)
```

Structure may evolve

## Architecture Questions

### How does Symbolic Memory work in AIGMos?

AIGMos does not rely on conversational context or hidden prompt history.

Instead, it is designed to operate on top of a structured symbolic memory layer where:

- memory is explicitly stored and inspectable
- runtime execution and memory are separated
- state transitions are deterministic

The underlying concept is described in:

https://github.com/Th3Hypn0tist/jit-symbolic-memory

LLM interaction is intended to operate on this symbolic layer rather than replacing it.

---

### What are the goals of the Architecture Alpha (Stage1)?

The current stage focuses on validating core principles:

- deterministic command execution
- explicit state management
- inspectable runtime behavior
- controlled integration of a single LLM call

This stage is not about features, but about proving architectural foundations.

---

### How does AIGMos differ from MemoryCore-Lite?

MemoryCore-Lite focuses primarily on structured memory modeling.

AIGMos extends this idea into a full runtime environment by adding:

- command execution pipeline
- deterministic task orchestration
- integration of symbolic memory with runtime actions

In short:

MemoryCore-Lite = memory model  
AIGMos = runtime built on top of that model

---

### What does AIGMos add to AI governance?

AIGMos explores a different paradigm for AI systems:

Instead of treating AI as autonomous agents, it treats AI as:

- a controlled execution component
- part of an inspectable runtime
- subject to deterministic workflows

This enables governance through structure rather than post-hoc monitoring.

---

### How is AIGMos intended to be used locally?

AIGMos is designed to run as a local runtime environment where:

- state is stored locally
- commands are executed deterministically
- LLM calls are made through explicit runtime actions

It is not designed as a hosted AI service or a cloud agent platform.

## Design Context

AIGMos explores an alternative approach to AI system architecture.

Many current AI tools are built around conversational interfaces and autonomous agent models.

In contrast, AIGMos is designed as:

- a deterministic runtime rather than a conversational endpoint
- a system with explicit command surfaces
- an environment where symbolic memory and execution are separated
- a framework where LLM interaction is governed rather than autonomous

The goal is to treat AI as **structured infrastructure** rather than opaque behavior.

## License

AIGMos uses a Business Source License (BUSL).

The core architecture is publicly accessible for research, testing, and internal use, while commercial rights remain reserved by the Licensor.
  
See LICENSE.md for details.
