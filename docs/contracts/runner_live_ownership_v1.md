# RUNNER LIVE OWNERSHIP v1

## Scope

This document locks the ownership boundary for the live runner runtime.

## Ownership split

- `system/runtime/runner.py` owns only live in-memory runtime state:
  - active runner registry
  - inflight jobs
  - worker loop
  - current step
  - transient status
  - last result / last error snapshots
- `system/runtime/runner_store.py` owns durable runner definitions:
  - persisted runner config
  - autostart metadata
  - durable definition updates
- `Parser.parse()` owns actual command execution.

## Rules

1. Runner live scheduling is not durable definition truth.
2. Durable runner definitions must not be mutated by `runner.py`.
3. Step command execution must remain attributable to `parser:<command>`.
4. Future live runner state writes, if added, must use `runner:<runner>` writer tags.
5. Runner and parser ownership must remain visibly distinct in metadata and docs.

## Current snapshot reading

In the current snapshot, `runner.py` does not directly write business state through the state API. It owns live scheduling and dispatch only. Because of that, STEP.9 in this snapshot is a boundary lock, not a large mutation refactor.

## Result

- `runner.py` = live runtime owner
- `runner_store.py` = durable definition owner
- `Parser.parse()` = execution owner
