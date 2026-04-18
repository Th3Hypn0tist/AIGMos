# AIGMos Canonical Specification v40

Status: clean canonical  
Scope: consolidated, de-duplicated, contradiction-free working spec  
Supersedes: v39

Revision note for v40:

```text
layout instance handle symbol is now "|"
canonical layout handle form = |<STORAGE_PREFIX>[.<instance_suffix>]
layout instances write to module-declared $ roots
one redraw path exists and only the active layout instance decides what is drawn
$ write policy is now policy-based: durable | buffered | volatile
coalescing is allowed only for snapshot/current-state writes, never for append-only history/log semantics
```

---
## 1. Identity

```text
AIGMos = AI realtime OS
       = HGI interface
```

Purpose: deterministic coordination runtime for humans, AI models, sensors, machines, modules, layouts, and external systems.

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
layout  = interactive surface bound to one active layout instance
```

Base rule:

```text
execution is explicit
there is no canonical scheduler tick in the base spec
external world sends data feeds only, never commands
```

---

## 3. Canonical Primitive Set

AIGMos uses seven canonical symbols:

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
| = layout instance handle
```

Notes:

- `$ # &` are the core data model.
- `! @ % |` are runtime objects.
- `#` is recursive by nature.
- `:` inside `#` paths must preserve both recursive hierarchy and `#cell:property = value` addressing.
- `|` is used only inside the AIGMos command surface and parser.

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

All persist canonically as strings.

Empty / null rules:

```text
empty RHS = syntax error
"" = valid empty string
canonical core has no null type
deletion must use rm
```

---

## 5. Assignment Semantics

Assignment form:

```text
<target> = <rhs>
```

Right-hand side may be one of:

```text
1 literal string / token
2 source reference
3 expression result where supported by context
```

Resolution rule:

```text
if rhs is a canonical source reference
its current value is resolved
and the resolved value is assigned
not the literal path text
```

Reference vs literal rule:

```text
prefixed token ($ # & ! @ % |) = reference
quoted token = explicit string literal
non-prefixed bare token = literal
in expressions, references always resolve to current value
```

Examples:

```text
$foo:bar = 1337
$foo:bar = start
$foo:bar = #OSC:9001:button:1
$foo:bar = $UM.sensor:temp
$SYSTEM:layout:active = |Q
trig !x $UM.module:mode == auto
trig !x $UM.module:mode == "auto"
```

Meaning of the references above:

```text
assign / compare against resolved current values
```

Empty / null semantics:

```text
empty RHS = syntax error
"" = valid empty string
canonical core has no null type
delete with rm, not with empty assignment
```

---

## 6. Namespaces and Paths

Namespace separator:

```text
:
```

Dot rule:

```text
. has no structural meaning
. is always just a valid character in names
```

Usermodule prefix rule:

```text
UM. is reserved as the usermodule prefix
canonical usermodule form = $UM.<module>:<field>
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

Parser never splits on dot unless a command defines a dot-bearing token family explicitly.

---

## 7. Path Segment Grammar

Segment rules:

```text
allowed chars in a segment = [A-Za-z0-9._]
"-" is not allowed
segment must not be empty
segment may start with a number
leading "." in a segment = syntax error
trailing "." in a segment = syntax error
```

Valid:

```text
#foo:1
#foo:01
#foo:bar.baz
#OSC:9001:button:1
$UM.module:mode
!trigger.1
@event.1
|Q.llama
```

Invalid:

```text
#OSC:button-1
$foo::bar
#foo:
#:
$UM.module:.mode
$UM.module:mode.
```

---

## 8. Whitespace and One-Line Rule

Whitespace rule:

```text
one or more whitespace characters
= exactly one separator
```

One line rule:

```text
one line = exactly one command
no multi-command syntax exists
```

Not allowed:

```text
cmd1 ; cmd2
cmd1 && cmd2
cmd1 | cmd2
```

---

## 9. Parser Order

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

There are no comments in the canonical grammar.

---

## 10. Quote Rule

Quotes are used only when a string or embedded command must be passed as one argument and it contains whitespace.

Form:

```text
"..."
```

Rules:

```text
single token string -> quotes not required
multi-part string   -> quotes required
embedded command    -> quotes required
```

Examples without quotes:

```text
start
run
build
255
HOT
run.build
$MEM.cmd:run.build
&MEM.queue:1
#MEM.jobs:0:1
%worker:status
!sensor.hot
@cooling.start
|Q.llama
```

Examples with quotes:

```text
"run &jobs"
"hello world"
"cp &MEM.queue:1 $MEM.current:1"
```

---

## 11. Locked Command Surface

```text
LOCKED_CORE_COMMANDS = [
  cp
  mv
  rm
  add
  merge
  on
  run
  loop
  trig
  new
  claim.root
  release.root
  claim.command
  release.command
  claim.command.alias
  release.command.alias
  claim.Q.alias
  release.Q.alias
  export.json
  import.json
  export.file
  import.file
  export.code
  import.code
  Q
  Qc
]

COMMAND_FAMILIES = [
  OSC
  HTTP.*
  Q
  Qc
  Q.alias
  Qc.alias
]

OPTIONAL_COMMANDS = [
  UM.*
]
```

Notes:

```text
emit is removed
add.item is replaced by add
OSC.* is removed
#OSC without port is removed
#OSC:in:... is removed
OSC:out:... is removed
paused is removed; canonical form is pause
```

### 11.1 Command Grammar

```text
cp                    <src> <dst>
mv                    <src> <dst>
rm                    <target>
add                   <target> <source>
merge                 <src> <dst>
Q                     [.<alias>] <query>
Qc                    [.<alias>] <output> <query>
trig                  <trigger_path> [<expr>]
on                    <trigger_path> <event_path> "<command>"
run                   "<command>"
run                   &<list>
run                   %<name> &<list>
run                   %<name> "command"
loop                  $<template>
loop                  #<table>
loop                  %<name> $<template>
loop                  %<name> #<table>
new                   |<handle> /<module>[.<alias>]
claim.root            <root> <target>
release.root          <root>
claim.command         <command>
release.command       <command>
claim.command.alias   <source> <alias>
release.command.alias <alias>
claim.Q.alias         <source> <alias>
release.Q.alias       <alias>
export.json           <output> <src>
import.json           <output> <src>
export.file           <output> <src>
import.file           <output> <src>
export.code           <output> <src>
import.code           <output> <src>
HTTP.GET              <output> <url>
HTTP.POST             <output> <url> <body>
HTTP.PUT              <output> <url> <body>
HTTP.DELETE           <output> <url>
HTTP.PATCH            <output> <url> <body>
HTTP.HEAD             <output> <url>
OSC:<port>:<path...>  <value>
```

Output-target rule:

```text
commands with an explicit output target always use token[1] as output
canonical output-target shape = foo <output> <input...>
this applies to Qc, import.*, export.*, and HTTP.*
commands without explicit output targets keep their own canonical signatures
```

Defaults:

```text
run %name &list    -> mode = runonce
run %name "command" -> mode = runonce
run &list          -> direct anonymous runonce execution
run "command"      -> direct anonymous single-command runonce execution
loop ...           -> mode = pause.first unless an explicit mode override exists
```

Name rules:

```text
run without %name does not create a persistent runner handle
loop may derive its name from the source
loop $foo.bar:doo         -> %foo.bar:doo
loop #jobs:queue          -> %jobs:queue
loop %custom $foo.bar:doo -> %custom
loop %custom #jobs:queue  -> %custom
if the final runner / loop name already exists -> ERR_STATE: name exists
layout instance names must be unique
if the final | handle already exists -> ERR_STATE: name exists
```

---

## 12. Bare Token / Reference / Expression Rules

Reference token:

```text
prefixed token ($ # & ! @ % |) = reference
```

Literal token:

```text
quoted token = explicit string literal
non-prefixed bare token = literal
single-token bare literal is allowed
multi-token string requires quotes
```

Expression rules:

```text
references always evaluate to current value
string literal may be bare or quoted
numeric-looking literal is allowed bare
```

Grouping rule:

```text
if an expression contains logical operators
AND / OR / XOR / NOT
group it with parentheses
```

Canonical operators:

```text
==
!=
<
<=
>
>=
AND
OR
XOR
NOT
```

---

## 13. Protected and Reserved Roots

### 13.1 Protected namespaces

Protected roots are readable but not normal free-write spaces.  
They may be mutated only by their owning canonical mechanism, except for the explicit field exceptions listed later.

Protected namespaces:

```text
$SYSTEM...
#SYSTEM...
#OSC...
#HTTP...
!...
@...
%...
|...
```

Owning mechanisms:

```text
$SYSTEM / #SYSTEM -> system / runtime / orchestration
#OSC              -> OSC adapter inbound
#HTTP             -> HTTP owning mechanism
!                 -> trig + trigger runtime
@                 -> on + event runtime
%                 -> run / loop runtime
|                 -> layout runtime
```

### 13.2 Reserved writable memory family

```text
MEM is reserved
writable memory-backed roots are:
- $MEM...
- &MEM...
- #MEM...
```

Meaning:

```text
$MEM... = memory-backed kv/object write
&MEM... = memory-backed list write
#MEM... = memory-backed structured write
```

---

## 14. Command Families

```text
OSC
HTTP.*
Q
Qc
Q.alias
Qc.alias
```

Data/read namespaces for transports:

```text
#OSC:...
#HTTP:...
```

Executable command surface:

```text
OSC:<port>:<path...> <value>
HTTP.GET ...
HTTP.POST ...
HTTP.PUT ...
HTTP.DELETE ...
HTTP.PATCH ...
HTTP.HEAD ...
Q ...
Qc ...
Q.alias ...
Qc.alias ...
```

---

## 15. Command Result Contract

Every command must return exactly one result:

```text
[ok]
[error: <reason>]
```

Rules:

```text
commands do not return payload data
all data flows through target writes
[ok] advances the runner
[error: <reason>] stops execution and sets runner status to error
```

All command/runtime errors must be appended to:

```text
#SYSTEM:error:log
```

---

## 16. Error Log and Log-Book Model

System error log target:

```text
#SYSTEM:error:log
```

Error log rules:

```text
every error entry must include the address/origin that caused the error
log target is an indexed dict
entry key = next numeric index
entry value = one CSV string
```

Minimum CSV content:

```text
timestamp,origin,error,reason
```

Log-book declaration:

```text
log <alias> <#target>
```

Operations:

```text
/show <alias>  = show bound log target
/clear <alias> = clear bound log target
log.list       = list all bound log-book aliases
```

Hard-coded clear shortcuts:

```text
/clear ch       = rm $CH
/clear ch.alias = rm $CH.alias
```

---

## 17. OSC Policy

### 17.1 Supported transport types

Supported:

```text
i = int32
f = float32
s = string
```

Not supported:

```text
b = blob
all other optional OSC types unless explicitly added later
bundles are not supported
```

AIGMos OSC accepts only:

```text
plain non-bundle OSC messages
exactly one argument per message
no zero-arg messages
no multi-arg messages
```

### 17.2 Inbound mapping

Canonical inbound form:

```text
#OSC:<port>:<path...>
```

Rules:

```text
port is mandatory
first segment after #OSC is the local listener port
remaining segments form the canonical path
#OSC is read-only inbound adapter state
direct assignment to #OSC:* = syntax error
```

### 17.3 Outbound command

Canonical outbound form:

```text
OSC:<port>:<path...> <value>
```

---

## 18. HTTP Policy

### 18.1 Inbound/read shape

```text
#HTTP:<id>:method
#HTTP:<id>:path
#HTTP:<id>:body
#HTTP:<id>:status
#HTTP:<id>:headers:<n>:name
#HTTP:<id>:headers:<n>:value
```

### 18.2 Command signatures

```text
HTTP.GET    <output> <url>
HTTP.POST   <output> <url> <body>
HTTP.PUT    <output> <url> <body>
HTTP.DELETE <output> <url>
HTTP.PATCH  <output> <url> <body>
HTTP.HEAD   <output> <url>
```

Rules:

```text
output is mandatory in all HTTP commands
output is always token[1]
body exists only in POST / PUT / PATCH
response data is always written to the caller-supplied # output target
output target must be a # path
canonical response shape is stored under that exact # branch
command result is only [ok] / [error: <reason>]
HTTP status code is response data, not command execution status
```

---

## 19. Remove / Copy / Move / Add / Merge Semantics

```text
rm &list:index     -> remove item and reindex
rm #table:row      -> remove row, no reindex
rm #table:row:cell -> remove cell value, no reindex
rm $kv:path        -> remove key/node
rm !trigger        -> remove trigger object
rm @event          -> remove event object
rm %runner         -> brutal kill
rm |layout         -> remove layout instance
```

### 19.1 Copy / Move Semantics

Canonical commands:

```text
cp <src> <dst>
mv <src> <dst>
```

General rule:

```text
copy preserves content semantics
move copies then removes source
```

Runtime restrictions:

```text
cp and mv do not apply to runtime spaces ! @ % |
rm does apply to runtime spaces by removing/stopping them
```

### 19.2 Add / Merge Rules

```text
add <target> <source>
merge <src> <dst>
```

Target-specific behavior:

```text
&list
- append only

$node
- greatest numeric child key + 1
- if none, start from 0

#table:row
- greatest numeric cell key + 1
- if none, start from 0
```

Rules:

```text
add applies only to $ # &
add $foo       = valid if $foo is a branch / object target
add $foo:bar   = syntax error
```

---

## 20. Trigger Model

### 20.1 Trigger types

```text
expr
onchange
cron
```

### 20.2 Trigger signatures

```text
trig !name <expr>
trig !name onchange <ref>
trig !name cron "spec"
```

### 20.3 Trigger fields

Allowed fields:

```text
!<name>:state
!<name>:pulse
```

Field rules:

```text
!<name>:state = runtime-owned, readable, values 0 / 1
!<name>:pulse = writable, numeric, unit always ms
```

---

## 21. Event Model

Canonical signature:

```text
on !trigger @event "command"
```

Rules:

```text
event names are unique
one event contains exactly one quoted command payload
direct assignment to @... = syntax error
```

---

## 22. Runner / Loop Model

### 22.1 % name parsing

Allowed % fields:

```text
%<name>:status
%<name>:step
%<name>:mode
%<name>:autostart
```

### 22.2 Status field

Allowed symbolic values:

```text
run
ok
stop
error
pause
```

Fixed numeric mapping:

```text
0 = run
1 = ok
2 = stop
3 = error
4 = pause
```

### 22.3 Step field

```text
%<name>:step accepts only integer values in range 0...N
```

### 22.4 Mode field

Allowed values:

```text
runonce
pause.first
loop
```

### 22.5 Autostart field

Allowed values:

```text
off
0
1
2
...
```

Rules:

```text
default = off
autostart only biases startup priority
autostart does not wait for previous autostart items to finish
equal-priority startup order has no canonical guarantee
OSC input is always system-autostart and is outside the % autostart sequence
```

---

## 23. run and loop Signatures

### 23.1 run

Canonical forms:

```text
run "command"
run &list
run %name &list
run %name "command"
```

Meaning:

```text
run "command"   = anonymous direct runonce of one command
run &list       = anonymous direct runonce of a list
run %name &list = named runonce runner
run %name "command" = named runonce single-command runner
```

### 23.2 loop

Canonical forms:

```text
loop $template
loop #table
loop %name $template
loop %name #table
```

Default:

```text
loop without explicit mode defaults to mode = pause.first
```

---

## 24. Layout Instance Model

### 24.1 Canonical handle form

Canonical layout handle:

```text
|<STORAGE_PREFIX>[.<instance_suffix>]
```

Examples:

```text
|Q
|Q.llama
|BUFFER
|BUFFER.log
|EDITOR
|EDITOR.promptit
```

Rules:

```text
base instance = plain module storage prefix
additional instances = storage prefix + "." + suffix
handle names are unique
active layout is stored in $SYSTEM:layout:active
```

Example:

```text
$SYSTEM:layout:active = |Q
```

### 24.2 Creation

Canonical creation form:

```text
new |<handle> /<module>[.<alias>]
```

Examples:

```text
new |Q /q
new |Q.llama /q.llama
new |BUFFER /buffer
new |BUFFER.log /buffer.log
new |EDITOR.promptit /editor.promptit
```

Rules:

```text
module route selects the module type
| handle selects the runtime layout instance handle
route alias and handle suffix must agree semantically
new on an existing handle = ERR_STATE
```

### 24.3 Module exports

A layout module must export at least:

```text
MODULE
TITLE
STORAGE_PREFIX
PRIMARY_WRITE_FIELD
create_instance(ctx, handle, config=None)
```

Optional exports:

```text
CONFIG_SCHEMA
DEFAULT_CONFIG
clone_instance(ctx, src_handle, new_handle)
restore_instance(ctx, handle, payload)
```

### 24.4 Derived write target

Final write target rule:

```text
$<STORAGE_PREFIX>[.<instance_suffix>]:<PRIMARY_WRITE_FIELD>
```

Examples:

```text
|Q              -> $Q:ch
|Q.llama        -> $Q.llama:ch
|BUFFER         -> $BUFFER:history
|BUFFER.log     -> $BUFFER.log:history
|EDITOR         -> $EDITOR:content
|EDITOR.promptit -> $EDITOR.promptit:content
```

### 24.5 Active layout and redraw

Rules:

```text
there is exactly one input surface
there is exactly one redraw path
only the active | layout instance decides what is drawn
background instances may update state but must not draw directly
modules never write directly to terminal output
```

### 24.6 Cross-instance query

Canonical rule:

```text
one layout instance may query another layout instance
response is written by default to the caller instance primary write target
callee does not gain redraw ownership
callee does not gain focus
```

Examples:

```text
|Q.llama query |BUFFER.log
-> response target = $Q.llama:ch

|BUFFER.log query |Q
-> response target = $BUFFER.log:history
```

Optional instance hooks:

```text
query(target, payload)
on_query(payload)
on_response(source, payload)
serialize()
restore(payload)
```

---

## 25. Claiming, Aliases, Q / Qc, and Ownership

```text
claim.root            <root> <target>
release.root          <root>
claim.command         <command>
release.command       <command>
claim.command.alias   <source> <alias>
release.command.alias <alias>
claim.Q.alias         <source> <alias>
release.Q.alias       <alias>
```

### 25.1 Q / Qc and LLM Aliases

```text
Q  [.<alias>] <query>
Qc [.<alias>] <output> <query>
claim.Q.alias   <source> <alias>
release.Q.alias <alias>
```

Semantics:

```text
Q
- writes to $CH

Q.<alias>
- writes to $CH.<alias>

Qc
- explicit output target
- output is token[1] after the command token / alias token
```

---

## 26. Import / Export Commands

Canonical grammar:

```text
export.json <output> <src>
import.json <output> <src>
export.file <output> <src>
import.file <output> <src>
export.code <output> <src>
import.code <output> <src>
```

Output-target rule:

```text
all import/export commands use output-first ordering
output is always token[1]
```

---

## 27. Error Model

```text
ERROR_TYPES = [
  ERR_SYNTAX
  ERR_EVAL
  ERR_RUNTIME
  ERR_ADAPTER
  ERR_OWNERSHIP
  ERR_NOT_FOUND
  ERR_TYPE
  ERR_STATE
]
```

---

## 28. $ Write Policy

AIGMos $ writes are policy-based.

Policies:

```text
durable
buffered
volatile
```

Semantics:

```text
durable
- canonical success point requires durable persistence

buffered
- update becomes visible immediately in live state
- persistence may be coalesced / flushed later according to policy

volatile
- state lives only in memory
- no durable persistence is required
```

Guidance:

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
$Q.llama:ch
- snapshot/current-state
- coalescing allowed

$BUFFER:history
- history
- append semantics matter
- no silent coalescing away of entries

#SYSTEM:error:log
- append-only log
- each entry matters
```

---

## 29. System Policies

### 29.1 SQLite policy

```text
sqlite per instance
```

Meaning:

```text
each AIGMos instance owns its own SQLite
shared multi-instance truth should use a server database or another shared-store mechanism
```

### 29.2 External feed rule

```text
external world never sends canonical commands directly
external integrations write feeds into claimed roots
commands execute only inside the command surface
```

---

## 30. Short Canonical Summary

```text
storage is string-only
execution is explicit
commands return only [ok] or [error: <reason>]
data never returns through command results
OSC is single-message, single-argument, no-bundle
HTTP writes response data into #HTTP:<id>:...
triggers are expr / onchange / cron
events bind one trigger to one quoted command
run = runonce by default
loop = pause.first by default
runner fields are :status / :step / :mode / :autostart
autostart only biases startup priority
| is the canonical layout instance handle
new creates layout instances
layout modules export STORAGE_PREFIX and PRIMARY_WRITE_FIELD
only the active | layout instance decides what is drawn
cross-instance query writes back to caller primary target by default
$ writes are policy-based: durable / buffered / volatile
coalescing is only for snapshot/current-state, never append-only history/log semantics
MEM is reserved writable memory family
errors append to #SYSTEM:error:log
```
