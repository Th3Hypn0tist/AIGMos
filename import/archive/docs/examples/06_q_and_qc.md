# 06_q_and_qc

Minimal examples for the `Q` and `Qc` command family.

## `Q`

History-oriented interaction.

```text
Q "Explain what `run %main &boot` does"

ls $CH
cat $CH:00000
cat $CH:00001
```

What this shows:

- `Q` is chat/history-oriented
- responses are written into chat history
- the history can be inspected like other state

## `Qc`

Single-shot request with explicit output.

```text
mk $results
Qc $results:summary "Summarize the current command model in two sentences"
cat $results:summary
```

Alias-oriented form when a provider alias is configured:

```text
Qc .coder $results:patch "Return only the updated function body"
cat $results:patch
```

What this shows:

- `Qc` is for single-shot work
- output goes to an explicit target
- output-first direction stays consistent with the rest of the command surface
- normalized output should resolve to text, list, or dict
