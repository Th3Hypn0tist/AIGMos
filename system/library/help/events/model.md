# Event Model

## Relationship to other runtime objects

- `!` = trigger
- `@` = event
- `%` = runner

### Difference

- trigger decides *when*
- event says *what command to dispatch*
- runner decides *how repeatedly or in what mode something executes*

## Canonical behavior

- event is queued
- queue is FIFO
- parser executes the event command

## What an event is not

- not its own scripting language
- not a multi-step workflow by itself
- not a trigger alias
- not a persistent service loop
