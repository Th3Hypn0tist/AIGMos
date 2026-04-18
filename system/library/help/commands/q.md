# Q Commands

Commands for stateful and stateless model calls.

## q

```text
q[.profile] <target> <prompt...>
```

Stateful chat command.

Rules:
- target is explicit
- dispatches query asynchronously
- does not return successful assistant output to the command buffer
- writes prompt and status into the target q runtime
- same concrete q target runs one active job at a time
- additional jobs for the same q target wait in queue and may show `[WAITING]` or `[CUE N/X]` in the UI

Examples:

```text
q |:q |Q:q hello
q |HELP:q explain #HELP:README.md
q.coder |Q:q refactor this
```

## qc

```text
qc[.profile] <output> <prompt...>
```

Stateless structured q call.

Rules:
- output target is explicit
- no chat history is written
- accepted decoded output types: string, list, dict
- returns `[ok]` after writing decoded output to target

Examples:

```text
qc $OUT hello
qc.coder $OUT $prompt
```
