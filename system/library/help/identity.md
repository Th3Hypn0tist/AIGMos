# Identity

## Canonical definition

AIGMos is a local-first orchestration and control runtime for humans, AI, sensors, machines, layouts, and external systems.

It acts as an AI realtime OS built around a single symbolic command surface. State, events, triggers, runners, layouts, and AI instances are coordinated through explicit symbolic commands.

## What AIGMos is

- an orchestration runtime
- a symbolic state system
- a command-surface-driven control layer
- a runtime for layouts, modules, events, triggers, runners, and AI instances
- a local-first foundation that can talk to external systems

## What AIGMos is not

- not primarily a chat framework
- not just a UI shell around an LLM
- not only `q` and `qc`
- not just a layout engine
- not just a trigger engine
- not just a state database

## Correct mental model

Use this model first:

```text
AIGMos = symbolic orchestration runtime / AI realtime OS
```

Not this model:

```text
AIGMos = chat interface framework
```

## Position of q and qc

`q` and `qc` are operator-facing AI modules inside the larger runtime.
They are important, but they do not define the whole system.

## Operator summary

If asked "what is AIGMos?", start from:

- runtime
- orchestration
- command surface
- state
- events / triggers / runners
- layouts / modules
- AI modules as part of the whole
