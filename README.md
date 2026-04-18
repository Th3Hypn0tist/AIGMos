# AIGMos

AIGMos is a deterministic command-surface runtime for structured AI, automation, and terminal-first control.

It is designed around explicit state, explicit commands, and inspectable runtime behavior. The goal is not to hide behavior behind chat. The goal is to make behavior visible, bounded, debuggable, and composable.

This repository should be read as an active working runtime, not as a polished consumer product.

---

## What AIGMos is

AIGMos can be read as:

- an AI realtime OS
- an HGI command surface
- a local-first orchestration runtime
- a deterministic control layer for humans, AI models, sensors, machines, layouts, and external systems

The canonical runtime chain is intentionally simple:

```text
signals -> state -> triggers -> events -> execution -> output -> signals
```

Everything important is meant to be explicit:

- explicit state
- explicit ownership
- explicit dispatch
- explicit runtime objects
- explicit inspection through the command surface

---

## Current snapshot

The current working model uses:

- `|` for layout instance handles
- lowercase `q` and `qc`
- `new |<instance> /<layout-or-module>` for layout creation
- terminal-first layout instances such as `|CS`, `|Q`, `|HELP`, and custom `|...` instances
- per-instance runtime state
- `|...` as the source of truth for layout-instance runtime data

If an older spec or contract file disagrees with the current code snapshot, treat the current code and locked rules as authoritative.

---

## Core mental model

### State primitives

- `$` = key/value state
- `#` = structured namespace / tree state
- `&` = ordered indexed list state

### Runtime primitives

- `!` = trigger
- `@` = event
- `%` = runner
- `|` = layout instance

### Key distinction

- `$ # &` are the canonical data model
- `! @ % |` are runtime objects
- `|` is its own symbol space and must not be mixed with `$`

---

## Design principles

AIGMos is built around a few hard constraints:

- deterministic behavior beats hidden convenience
- visible runtime beats opaque orchestration
- inspectable state beats implicit magic
- one command surface is better than many disconnected control paths
- local control matters
- legacy layers should be removed instead of preserved without reason

This produces a system where behavior can be traced, replayed, reasoned about, and corrected without guessing what a hidden framework is doing.

---

## Layouts and instances

Layouts are real runtime instances.

Examples:

```text
|CS
|Q
|HELP
|Q.llama
|BUFFER.log
```

Important rules:

- `|instance` is the identity source
- the active layout instance decides what is rendered
- layout runtime data belongs under `|...`
- layout-instance persistence belongs to `|...`
- `|` stays separate from `$` semantics

Typical examples:

```text
new |Q /q
new |HELP /help
|HELP:q:role:think = true
|HELP:q:role:view_thinking = false
```

---

## Q and QC

AIGMos has two different LLM-facing command forms.

### `q`

`q` is the stateful chat form.

It uses instance-owned runtime state and is intended to work with bound layout instances.

Examples:

```text
q hello
q.qwen explain #SYSTEM:config:q
```

### `qc`

`qc` is the stateless single-shot form.

It is intended for targeted output generation instead of session-style chat ownership.

Examples:

```text
qc $OUT summarize #SYSTEM:config
qc.qwen $PATCH return only the final patch plan
```

### Locked q logic

The current locked model is:

```text
stream = gate
think = payload-intent
view_thinking = UI-only
```

Meaning:

#### `stream`

- controls transport mode
- `stream = true` -> payload includes `"stream": true`
- `stream = false` -> non-stream path; think is ignored in practice

#### `think`

- controls which payload fragment is merged
- `think = true` -> merge `think_payload`
- `think = false` -> merge `nothink_payload`
- this is payload intent, not a UI flag

#### `view_thinking`

- controls only what is shown in the UI
- `view_thinking = true` -> show actual thinking output
- `view_thinking = false` and `think = true` -> show only `[Thinking...]`
- it must not affect payload building, parsing, or stream selection

### Ownership rule

- `q` reads runtime state from `|<instance>:<q_id>:*`
- `qc` reads canonical role data from `#ROLES:*`
- no silent fallback from `q` to canonical role source during payload build
- no silent fallback from `qc` to instance runtime

---

## Events, triggers, and runners

### `!` triggers

A trigger is a passive condition or pulse object.

It does not execute the command itself.

### `@` events

An event is a passive object that binds one trigger or caller action to one command.

Important rules:

- one event = one command
- events are dispatched through the parser
- events are not triggers
- events are not runners
- events are not their own scripting language

### `%` runners

Runners execute commands in runtime context.

They are used for loops, recurring execution, and bounded runtime workflows.

---

## What the repository currently includes

The current repository contains the working core for:

- command surface and parser
- persistent state backends
- triggers, events, and runners
- terminal-first layout runtime
- layout DSL
- built-in layout modules such as `cs`, `monitor`, `q`, and `qmon`
- q / qc integration
- import/export helpers
- mapping helpers
- extension hooks for commands, inputs, adapters, layouts, and roles

---

## Quick start

### 1. Start the runtime

```text
python AIGMos.py
```

A valid `config.json` is required.

### 2. Create some state

```text
mk $texts
set $texts:title AIGMos
mk &steps
add &steps "echo hello"
add &steps "echo world"
ls $
cat $texts:title
```

### 3. Create a q layout

```text
new |Q /q
```

### 4. Open a help layout

```text
new |HELP /help
```

### 5. Try q runtime settings

```text
|HELP:q:role:stream = true
|HELP:q:role:think = true
|HELP:q:role:view_thinking = false
```

### 6. Inspect payload debug

```text
cat |HELP:q:debug:transport:request_payload
```

---

## Typical command examples

### State

```text
mk $notes
set $notes:title test
cat $notes:title
```

### Layouts

```text
new |HELP /help
|HELP
```

### Trigger -> event

```text
trig !ready $SYSTEM:mode == run
on !ready @start "run %main &boot"
```

### Q

```text
q hello
qc $OUT summarize #SYSTEM:config
```

### Import/export

```text
import.file README.md $DOC
export.file $DOC out.txt
map.structure #SYSTEM
map.files ./system
```

---

## Documentation map

Recommended reading order:

- `docs/README.md`
- `docs/examples/01_quickstart.md`
- `docs/examples/06_q_and_qc.md`
- `docs/specs/COMMANDS.md`
- `docs/specs/RUNTIME.md`
- `docs/specs/q-logic.md`
- `docs/specs/q-payload.md`

Help-oriented material lives under both:

- `docs/help/`
- `system/library/help/`

Historical and canonical contracts live under:

- `docs/contracts/`
- `docs/specs/`

Older documents remain useful context, but some are intentionally historical. Use the current code and locked runtime rules when there is a conflict.

---

## Help bundle and bot reference data

The project includes help/reference material intended not only for humans, but also as bot-facing guidance data.

The practical purpose of the help bundle is to give the bot a grounded reference for:

- current AIGMos concepts
- valid commands
- symbol behavior
- locked runtime rules
- common mistakes
- troubleshooting patterns

That means the help bundle should be written as a factual reference layer, not as vague product copy.

---

## Current caveats

This repository is moving fast.

That means:

- some older docs describe earlier layouts or ownership rules
- some names in historical files are preserved for context only
- some cleanup work may still exist around legacy compatibility paths

The working rule remains:

```text
current code + locked rules > older descriptive documents
```

---

## License

AIGMos uses the Business Source License.

See `LICENSE.md` for the current license text.
