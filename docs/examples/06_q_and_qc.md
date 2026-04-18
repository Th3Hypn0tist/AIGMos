# 06_q_and_qc

Minimal current-snapshot examples for the `q` and `qc` command family.

## `q`

Stateful / history-oriented interaction.

```text
new |Q /q
q "Explain what run %main &boot does"

cat $Q:ch
```

What this shows:

- `q` is the chat/history-oriented command
- in a layout context, q state is typically instance-owned
- history can be inspected through the resolved q state root

## `qc`

Single-shot request with explicit output.

```text
mk $results
qc $results:summary "Summarize the current command model in two sentences"
cat $results:summary
```

Alias-oriented form when a provider profile is configured:

```text
qc.qwen $results:patch "Return only the updated function body"
cat $results:patch
```

What this shows:

- `qc` is for single-shot work
- output goes to an explicit target
- `q` and `qc` are lowercase in the current code
