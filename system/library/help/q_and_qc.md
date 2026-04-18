# q and qc

## Summary

`q` and `qc` are AI modules inside AIGMos.
They are not the definition of AIGMos itself.

## q

`q` is the stateful chat-style module.
Typical runtime data lives under the active `|` instance.

Examples:

```text
|HELP:q:ch
|HELP:q:role:think
|HELP:q:role:stream
|HELP:q:role:view_thinking
```

## qc

`qc` is the more structured single-call module.
Use it when you want decoded / targeted output rather than a chat history loop.

## Why both exist

- `q` fits conversational or iterative operator interaction
- `qc` fits more constrained structured tasks

## Do not overdefine the system by these modules

Correct:

```text
AIGMos contains q and qc.
```

Incorrect:

```text
AIGMos is mainly a q/qc chat framework.
```
