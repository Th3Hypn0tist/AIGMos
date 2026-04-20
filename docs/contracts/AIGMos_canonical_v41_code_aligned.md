# AIGMos Canonical Specification v41

Status: code-aligned working canonical  
Scope: current uploaded `system.zip` behavior  
Supersedes: v40 as the primary baseline for this draft

## Revision note for v41

This revision aligns the canonical to the uploaded code snapshot rather than to thread-only future locks.

Main corrections relative to v40:

- `q` and `qc` are lowercase in the command surface.
- the implemented built-in command surface is broader than v40 and includes utility commands such as `bind`, `binds`, `unbind`, `set`, `get`, `mk`, `ls`, `cat`, `map.files`, `map.structure`, `echo`, `emit`, `cycle`, `hget`, `hpost`, and `import.list`.
- `new` currently works as `new |<instance> /<module-or-layout>`.
- layout runtime currently has two distinct creation paths:
  - direct module instance creation
  - bound layout-definition creation from `.tmpl`
- startup currently ensures `|CS`.
- q state ownership is currently hybrid:
  - direct `|Q` and `|Q.<suffix>` instances map to `$Q` and `$Q.<suffix>`
  - q self-route from other active layout handles falls back to profile-based q roots
- q role/system prompt support is currently plain-symbol based under q state; `#ROLES` and `.role` packages are not part of this uploaded code snapshot.
- layout root XML attrs are parsed, but the authoritative route identity is the template filename / requested route, not `<layout name="...">`.
- `/reload layout` currently rebuilds runtime through the persisted layout store and bootstrap path; a guaranteed fresh-disk-only reload is not yet canonical in this uploaded snapshot.

---

## 1. Identity

```text
AIGMos = AI realtime OS
       = HGI interface
```

Purpose: deterministic coordination runtime for humans, AI models, sensors, machines, layouts, modules, and external systems.

---

## 2. Canonical Runtime Chain

```text
signals
→ state
→ triggers
→ events
→ run | loop
→ output
→ signals
```

Responsibility split:

```text
trigger = passive boolean / pulse object
event   = passive object binding one trigger to one command
run     = transient execution + mutation
loop    = runner behavior using the same execution core
layout  = interactive surface bound to one active layout handle
```

Base rule:

```text
execution is explicit
there is no canonical scheduler tick in the base spec
external world sends data feeds only, never commands
```

---

## 3. Canonical Primitive Set

AIGMos currently uses seven canonical symbols in the command surface:

```text
$
#
&
!
@
%
|
```

Primitive roles:

```text
$ = object field state
# = structured-address namespace
& = ordered indexed list
! = passive trigger object
@ = passive event object
% = runner / loop runtime handle
| = layout handle
```

Notes:

- `$ # &` are the core data model.
- `! @ % |` are runtime objects.
- `#` is recursive by nature.
- `:` inside `#` paths must preserve both recursive hierarchy and `#cell:property = value` addressing.
- `|` is an AIGMos parser/runtime symbol, not a shell pipe.

---

## 4. Canonical Type Model

```text
all canonical stored values are strings
context determines operational type and meaning
runner / expression / adapter layers may coerce values temporarily during execution
no canonical int, float, bool, or null types exist at storage level
```

Examples:

```text
$foo:n    = 1
$foo:f    = 3.14
$foo:flag = true
```

Empty / null rules:

```text
empty RHS = syntax error
"" = valid empty string
canonical core has no null type
delete with rm
```

---

## 5. Namespaces and Paths

Namespace separator:

```text
:
```

Dot rule:

```text
. has no structural meaning by itself
. is a valid character in names
parser does not split on dot unless a command family defines that behavior explicitly
```

Examples:

```text
$UM.sensor:temp
#OSC:9001:button:1
#HTTP:1:body
&rutiini.eka:0
!sensor.hot
@cooling.start
%foo.bar:doo:status
|Q.llama
```

Path segment rules:

```text
allowed chars in a segment = [A-Za-z0-9._]
"-" is not allowed
segment must not be empty
segment may start with a number
leading "." in a segment = syntax error
trailing "." in a segment = syntax error
```

---

## 6. Parser Order

A line is always one of:

```text
1 event declaration
2 assignment
3 command
```

Parser order:

```text
1 trim whitespace
2 if starts with "on " -> event
3 else if contains "=" -> assignment
4 else -> command
```

There are no canonical comments in the grammar.

---

## 7. Implemented Built-In Command Surface

Current built-in commands in the uploaded code snapshot are:

```text
/
add
bind
binds
cat
cp
cycle
echo
emit
export.code
export.file
export.json
get
hget
hpost
import.code
import.file
import.json
import.list
loop
ls
map.files
map.structure
mk
mv
new
on
q
qc
rm
run
set
trig
unbind
```

Notes:

- extension commands may add more commands at runtime.
- lowercase `q` and `qc` are canonical for this code-aligned revision.
- slash subcommands are part of the `/` command, not separate top-level commands.

---

## 8. Slash Surface

Implemented slash subcommands are:

```text
/help [cmd]
/time
/greeting
/clear
/reload [config|commands|layout|adapters|inputs|all]
/q[.<alias>]
/monitor[.<alias>]
/health q[.<alias>]
/exit
```

Notes:

```text
/reload with no target defaults to config
/editor returns an explicit legacy error
/help text still mentions /cs, but /cs is not implemented in this uploaded code snapshot
```

---

## 9. Assignment / Reference Rules

Reference token:

```text
prefixed token ($ # & ! @ % |) = reference
```

Literal token:

```text
quoted token = explicit literal
non-prefixed bare token = literal
multi-token literal requires quotes
```

Examples:

```text
$foo:bar = 1337
$foo:bar = start
$foo:bar = #OSC:9001:button:1
$SYSTEM:layout:active = |Q
```

---

## 10. Storage and Write Policy

Current code remains aligned with policy-based `$` writes:

```text
durable
buffered
volatile
```

Operational guidance:

```text
$SYSTEM:*    -> usually durable
$Q:*         -> usually buffered
$BUFFER:*    -> usually buffered
$MEM:*       -> volatile
layout dirty/render helpers -> volatile
```

Coalescing rule:

```text
coalescing is allowed only for snapshot/current-state writes
coalescing is not allowed for append-only history/log semantics where each step matters
```

Examples:

```text
$Q.llama:ch      -> snapshot/current-state style q history object
$BUFFER:history  -> append semantics matter
#SYSTEM:error:log -> append-only log
```

---

## 11. State Backend Policy

```text
default state backend = SQLite
sqlite is per instance
$MEM / &MEM / #MEM are temporary writable memory spaces
```

Meaning:

```text
each AIGMos instance owns its own SQLite
shared multi-instance truth should use a server database or another shared-store mechanism
```

---

## 12. Trigger Model

Implemented trigger forms:

```text
trig !name <expr>
trig !name onchange <ref>
trig !name cron "spec"
```

Allowed fields:

```text
!<name>:state
!<name>:pulse
```

Rules:

```text
!<name>:state = runtime-owned readable field
!<name>:pulse = writable millisecond field
```

---

## 13. Event Model

Canonical event declaration:

```text
on !trigger @event "command"
```

Rules:

```text
one event binds one trigger to one quoted command string
event names are unique
rm @event removes the event object
```

---

## 14. Runner / Loop Model

Runner fields:

```text
%<name>:status
%<name>:step
%<name>:mode
%<name>:autostart
```

Status values:

```text
run
ok
stop
error
pause
```

Numeric mapping:

```text
0 = run
1 = ok
2 = stop
3 = error
4 = pause
```

Run forms:

```text
run "command"
run &list
run %name "command"
run %name &list
```

Loop forms:

```text
loop $template
loop #table
loop %name $template
loop %name #table
```

Defaults:

```text
run  -> runonce
loop -> pause.first
%<name>:autostart default = off
```

Runtime-space restriction:

```text
cp / mv do not apply to ! @ % |
rm does apply to ! @ % |
```

---

## 15. Data Commands

Current built-ins around state/data manipulation include:

```text
mk
set
get
ls
cat
cp
mv
rm
add
merge
map.files
map.structure
import.file
import.json
import.code
import.list
export.file
export.json
export.code
```

Current locked operational direction remains:

```text
add applies only to $ # &
cp / mv do not apply to runtime spaces
```

---

## 16. HTTP and OSC

Implemented HTTP-related commands:

```text
hget
hpost
HTTP.GET
HTTP.POST
HTTP.PUT
HTTP.DELETE
HTTP.PATCH
HTTP.HEAD
```

Implemented OSC model:

```text
#OSC:<port>:<path...> for inbound readable state
OSC:<port>:<path...> <value> for outbound send
```

High-level policy remains:

```text
external world writes feeds into state surfaces
external world does not inject canonical commands directly
```

---

## 17. q / qc Command Family

Current command heads:

```text
q[.<profile>] <prompt...>
qc[.<profile>] <output> <prompt...>
```

### 17.1 q

Semantics:

```text
q is stateful chat
q streams live output
q writes chat history
q may use an optional profile suffix
```

Examples:

```text
q hello
q $prompt
q.coder explain #code:main
```

State used by q:

```text
:ch
:response
:thinking_text
:prompt
:error
:role
:system_prompt
```

Current implementation detail:

```text
role and system_prompt are plain q-state symbols
there is no canonical #ROLES package layer in this uploaded snapshot
```

### 17.2 qc

Semantics:

```text
qc is stateless
qc requires an explicit output target
qc does not write automatic q chat history
accepted decoded output types are string, list, dict
successful qc writes payload to the explicit target and returns [ok]
```

Examples:

```text
qc #out hello
qc.coder #out $prompt
```

Output target rule:

```text
qc output must start with $, #, or &
```

---

## 18. q Profile and State Resolution

Current q profile config sources are:

```text
#SYSTEM:config:q
#SYSTEM:config:q:default
#SYSTEM:config:q:<profile>
```

Current q runtime/state override sources are:

```text
$Q:<key>
$Q.<profile>:<key>
```

Sampler/runtime keys read from q state may include things such as:

```text
temperature
top_k
top_p
repeat_penalty
stop
max_tokens
seed
num_ctx
thinking
think
```

Current symbol resolution rule for q state prefix:

```text
if layout caller handle is |Q       -> q state prefix = $Q
if layout caller handle is |Q.<x>   -> q state prefix = $Q.<x>
otherwise                           -> q state prefix falls back to profile-based $Q / $Q.<profile>
```

This means the current implementation is not yet fully "one chat root per arbitrary layout instance".

It is currently:

```text
direct q-instance aware for |Q / |Q.<suffix>
profile-based otherwise
```

---

## 19. q Live Rendering Model

Current q live rendering behavior is:

```text
while streaming and no visible response yet -> show [THINKING] ...
while streaming with visible response        -> show [RESPONSE] ...
after live session completes                -> render chat history from :ch
```

q chat history object shape is currently:

```text
$Q[:.<profile-or-suffix>]:ch:<n>:prompt
$Q[:.<profile-or-suffix>]:ch:<n>:response
$Q[:.<profile-or-suffix>]:ch:<n>:done
```

Examples:

```text
$Q:ch:1:prompt
$Q:ch:1:response
$Q.llama:ch:4:done
```

---

## 20. Layout Runtime Overview

Current layout runtime has two distinct object classes:

```text
1 direct module instances
2 bound layout-definition handles
```

### 20.1 Direct module instance

A direct module instance is created from a module route when the route does not resolve to a `.tmpl` layout definition.

Examples:

```text
new |q /q        -> |Q
new |llama /q.llama -> |Q.llama
new |main /buffer   -> |BUFFER.main
```

Root-instance rule in current code:

```text
if instance token == module name
-> use the root STORAGE_PREFIX handle
else
-> use STORAGE_PREFIX + "." + instance token
```

### 20.2 Bound layout-definition handle

A bound layout-definition handle is created when the route resolves to a `.tmpl` tree.

Examples:

```text
new |main /cs
new |desk /q
new |ops /xx
```

In this path:

```text
|<instance> is the parent binding handle
child module instances are generated under the hood
```

The parent binding handle owns:

```text
|<handle>:buffer
|<handle>:meta:*
```

Child module instances are generated from module prefixes and ordinals.

---

## 21. Layout Handle Rules

Current handle rules:

```text
layout handles start with |
normalize_handle() uppercases the head segment before any dot suffix
":" is not allowed inside a layout handle
```

Examples:

```text
|Q
|Q.llama
|BUFFER.main
|OPS
```

Current startup rule:

```text
bootstrap ensures |CS
|CS is the default startup layout handle
```

Active layout pointer:

```text
$SYSTEM:layout:active is mirrored through layout runtime meta
runtime also keeps active_handle in layout runtime memory
```

---

## 22. `new` Command Semantics

Current grammar:

```text
new |<instance> /<module-or-layout>
```

Important current-code rule:

```text
new does not currently take the v40-style canonical form new |<full-handle> /<module>[.<alias>]
```

Instead:

```text
| token = user-supplied instance token
/ route  = module route or layout-definition route
final handle may be derived from STORAGE_PREFIX when creating a direct module instance
```

Examples:

```text
new |q /q            -> creates |Q
new |llama /q.llama  -> creates |Q.llama
new |main /cs        -> creates binding |MAIN
new |ops /xx         -> creates binding |OPS
```

This is one of the largest code-vs-v40 drifts.

---

## 23. Layout Module Contract

Required module exports in current code:

```text
MODULE
STORAGE_PREFIX
DEFAULT_PROMPT
FOCUSABLE
get_targets(handle, config=None)
measure(ctx, binding_handle, spec, width, instance)
build_payload(ctx, binding_handle, spec, rect, instance)
```

Optional module hooks observed in current code:

```text
handle_key(ctx, module_handle, key)
clear(ctx, module_handle, instance)
```

Current built-in layout modules are:

```text
cs
editor
label
list
monitor
q
viewer
```

Notes:

```text
qmon is not part of this uploaded code snapshot
editor and viewer still exist in this snapshot even if they are not the desired long-term direction
```

---

## 24. Layout Template DSL

Current template source paths:

```text
system/library/layout/*.tmpl
extensions/layout/*.tmpl
```

Current built-in templates in the uploaded snapshot are:

```text
cs.tmpl
q.tmpl
qcs.tmpl
xx.tmpl
```

Current DSL shape:

```text
<layout>
  <row>
    <cell>
      <leaf>
```

Containers:

```text
layout
row
cell
```

Leafs are tokenized from start-tags and flattened into specs.

Current practical rule:

```text
template filename / route is authoritative
root attrs such as <layout name="..."> are parsed but not authoritative identity
```

Current code does not yet make `<layout title="...">` a canonical default-title mechanism.

---

## 25. Layout Input and Rendering

Current high-level rules:

```text
there is one input surface
there is one redraw path
only the active handle determines what gets painted
background instances may update state but do not paint directly
```

Input dispatch behavior:

```text
if line starts with | and is a clean handle switch -> switch active layout
if line routes to parser -> echo command to current layout buffer and parse it
if active target resolves to q -> plain text self-routes asynchronously to q
otherwise -> no-op unless module/key handling consumes it
```

The current command echo path appends:

```text
> <command>
```

into the active layout buffer target.

---

## 26. Layout Buffers and Meta

Current layout/runtime meta is stored under layout-owned symbols such as:

```text
|<handle>:buffer
|<handle>:meta:module
|<handle>:meta:title
|<handle>:meta:prompt
|<handle>:meta:status
|<handle>:meta:view_target
|<handle>:meta:modules
|<handle>:meta:active_module
```

Current code uses a dedicated `|LAYOUT` meta area for active-handle persistence.

---

## 27. Layout Module Targeting Rules

Current built-in target behaviors:

### 27.1 cs

```text
primary/view target = |<module-handle>:buffer
focusable = true
DEFAULT_PROMPT = "cs> "
<cs lines=n> is supported
```

### 27.2 monitor

```text
view target comes from config target
for bound layouts, alias="|" resolves to the parent binding handle buffer
explicit alias targets are converted to <alias>:buffer in current code
```

### 27.3 label

```text
label resolves input via symbols or special |:meta forms
|:handle is supported
|:<key> reads |<current-handle>:meta:<key>
```

### 27.4 q

```text
q module uses state_handle from config when provided
q direct roots are $Q / $Q.<suffix> for handles |Q / |Q.<suffix>
q clear resets :ch, :response, :thinking_text, :prompt, :error
```

---

## 28. `/reload layout` Semantics

Current implemented behavior:

```text
reload_layout(ctx)
- clears runtime bindings and instances
- marks layout runtime unbootstrapped
- bootstraps again
- restores persisted layout store payload when available
- tries to restore the previous active handle
- falls back to |CS on failure
```

Important current-code note:

```text
layout reload is currently store-driven
fresh-disk-only reparsing of templates is not yet a guaranteed canonical property in this uploaded snapshot
```

---

## 29. Boot and Autostart Policy

Boot order remains:

```text
1 system runtime initialization
2 system input surfaces
3 inbound OSC listeners
4 runner autostarts
5 steady-state runtime
```

Rules:

```text
OSC input is always part of system boot
OSC input is not part of % runner autostart sequencing
only runners with %<name>:autostart != off are started in the autostart phase
priority biases launch order only
```

---

## 30. What Is Intentionally Not Canonical in v41

The following ideas may exist in thread decisions or later patch discussions, but they are not treated as canonical here because they are not present as a coherent part of the uploaded `system.zip` snapshot:

```text
#ROLES role-package runtime
.role JSON files
q/qc .r. role syntax
alias-based q job queues
/cancel |instance
qmon as a stable built-in module
<layout title="..."> as canonical default title
name="" on <layout> being explicitly ignored in code
full instance-owned q chat roots for arbitrary bound layout handles
fresh-disk-guaranteed /reload layout behavior
```

They may become canonical later, but not in this code-aligned revision.

---

## 31. Short Canonical Summary

```text
storage is string-only
execution is explicit
commands return only [ok] or [error: <reason>]
data does not return through command results
current built-in q commands are lowercase: q and qc
implemented built-in command surface is broader than v40
new currently uses: new |<instance> /<module-or-layout>
|CS is ensured at startup
layout runtime has both direct module instances and bound layout-definition handles
active layout is one | handle
there is one redraw path and only the active handle paints
q state ownership is currently hybrid: direct |Q / |Q.<suffix> roots plus profile fallback
roles are currently plain q-state text symbols, not #ROLES packages
/reload layout currently rebuilds through persisted layout store state
MEM remains temporary writable memory space
errors append to #SYSTEM:error:log
```
