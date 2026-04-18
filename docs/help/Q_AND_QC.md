# q and qc

This document describes the current code-facing behavior of `q` and `qc`.

---

## `q`

Syntax:

```text
q[.profile] <prompt...>
```

Examples:

```text
q hello
q.qwen explain #SYSTEM:config
q $PROMPT
```

### Current intent

`q` is the stateful chat command.

It:

- expands prompt symbols
- resolves a q profile
- loads chat history
- streams thinking/response state
- writes final chat entries into chat history

### Current state ownership

In the current code, `q` prefers the active layout caller handle when one exists.

Examples:

```text
|Q      -> $Q:ch
|HELP   -> $HELP:ch
|Q.llama -> $Q.llama:ch
```

If there is no active layout caller handle, it falls back to profile-based `$Q[.<profile>]` style roots.

That means the current code is layout-aware first, with profile fallback second.

### Current live fields

Typical q-related fields include:

```text
$X:ch
$X:response
$X:thinking_text
$X:role
$X:system_prompt
```

where `$X` is the resolved q state root for the current runtime context.

---

## `qc`

Syntax:

```text
qc[.profile] <output> <prompt...>
```

Examples:

```text
qc $OUT summarize #SYSTEM:config
qc.qwen $OUT return only the cleaned result
```

### Current intent

`qc` is a stateless explicit-output q call.

It:

- resolves the profile
- expands prompt symbols
- sends a single request
- decodes the provider output
- writes the final output to the caller-supplied target

Use `qc` when you do not want chat history behavior.

---

## q vs qc

Use `q` when you want:

- chat/history behavior
- a visible q instance
- streaming thinking/response

Use `qc` when you want:

- explicit output target
- single-shot processing
- no chat-history workflow

---

## Profiles

Current profile examples from `config.json` include:

- `default`
- `qwen`
- `dummyt`
- `grok`
- `openai`

Use them like this:

```text
q.qwen hello
qc.openai $OUT summarize #code:main.py
```

---

## Help-oriented usage

Typical help flow:

```text
new |HELP /help
```

Then use normal q prompts inside that help layout.

Practical examples:

```text
q explain new |HELP /help
q what does qmon do
q summarize current layout model
```

---

## Debugging cues

If q appears broken, check these first:

- does the target layout instance exist?
- does the selected profile exist in `config.json`?
- is the provider reachable?
- is the q state root being written where you expect?
- are you looking at `:ch` or only stale `:response`?
