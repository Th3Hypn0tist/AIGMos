# System Model

## Core execution idea

```text
signals -> state -> triggers -> events -> execution -> actions -> signals
```

AIGMos turns incoming inputs and internal state into explicit execution.

## Choke point rule

All intentional mutation goes through the command surface.

That means:

- commands mutate state
- events dispatch commands
- runners execute commands
- layouts route operator input into commands or modules

## Main runtime pieces

- state containers: `$`, `#`, `&`
- triggers: `!`
- events: `@`
- runners: `%`
- layout instances: `|`
- AI modules: `q`, `qc`

## High-level layering

1. command surface
2. state model
3. runtime objects (`!`, `@`, `%`, `|`)
4. layouts and modules
5. AI execution modules
6. external IO and adapters

## Why the model matters

The system should be explained from execution and control first, not from whatever module is currently visible on screen.
