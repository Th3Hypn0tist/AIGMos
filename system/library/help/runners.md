# Runners

## What `%` is

`%` is a runner object.

Runners execute work over time according to their mode.

## Relationship to events and commands

A runner is not the command itself.
It is the execution shell that may invoke commands or emit events.

## Main concepts

- once
- cycle
- loop
- status / lifecycle

## Mental model

```text
runner wakes -> executes command path -> may update state -> may emit events
```
