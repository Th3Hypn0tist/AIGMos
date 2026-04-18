# AIGMos Canonical Specification v37

Status: clean canonical  
Scope: consolidated, de-duplicated, contradiction-free working spec  
Supersedes: v36

Revision note for v37:

```text
named single-command runner is now canonical:
run %name "command"

add is now locked to $ # & only
- & appends directly
- $ and # append by next numeric child key
- if a non-numeric child exists under the add target, add = ERR_TYPE

cp / mv are now locked away from runtime spaces
- cp / mv do not apply to ! @ %
- rm still applies to ! @ % runtime objects

runner autostart is now canonical:
%<name>:autostart
- default = off
- numeric value enables boot autostart
- lower number tends to start earlier

layout runtime model is now canonical:
- one shared input surface
- active layout = instance id
- module type exports factory
- instance owns title / prompt / render / input handling

optional layout extensions are now explicitly allowed:
CONFIG_SCHEMA
DEFAULT_CONFIG
clone_instance()
serialize() / restore()
```

---
## 1. Identity

```text
AIGMos = AI realtime OS
       = HGI interface
```

Purpose: deterministic coordination runtime for humans, AI models, sensors, machines, modules, and external systems.

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
```

Base rule:

```text
execution is explicit
there is no canonical scheduler tick in the base spec
external world sends data feeds only, never commands
```

---

## 3. Canonical Primitive Set

AIGMos uses six canonical symbols:

```text
$
#
&
!
@
%
```

Primitive roles:

```text
$ = object field state
# = structured-address namespace
& = ordered indexed list
! = passive trigger object
@ = passive event object
% = runner / loop runtime handle
```

Notes:

- `$ # &` are the core data model.
- `! @ %` are runtime objects.
- `#` is recursive by nature.
- `:` inside `#` paths must preserve both recursive hierarchy and `#cell:property = value` addressing.

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
prefixed token ($ # & ! @ %) = reference
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

Valid:

```text
$foo:bar = ""
$foo:bar = 0
$foo:bar = false
$foo:bar = none
```

Invalid:

```text
$foo:bar =
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
```

Parser never splits on dot.

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

---

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
run                   %<name> "<command>"
run                   %<name> &<list>
loop                  $<template>
loop                  #<table>
loop                  %<name> $<template>
loop                  %<name> #<table>
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
run %name "command" -> mode = runonce
run %name &list     -> mode = runonce
run &list           -> direct anonymous runonce execution
run "command"       -> direct anonymous single-command runonce execution
loop ...            -> mode = pause.first unless an explicit mode override exists
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
```

---

## 12. Bare Token / Reference / Expression Rules

Reference token:

```text
prefixed token ($ # & ! @ %) = reference
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

Canonical examples:

```text
trig !x $UM.sensor:temp >= 40
trig !x ($UM.sensor:temp >= 40 AND $UM.heater:power < 70)
trig !x ($UM.module:mode == auto OR $UM.module:mode == manual)
trig !x (NOT ($UM.system:armed == 1))
trig !x (($A == 1) XOR ($B == 1))
```

Non-canonical:

```text
trig !x $A == 1 AND $B == 2
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
```

Owning mechanisms:

```text
$SYSTEM / #SYSTEM -> system / runtime / orchestration
#OSC              -> OSC adapter inbound
#HTTP             -> HTTP owning mechanism
!                 -> trig + trigger runtime
@                 -> on + event runtime
%                 -> run / loop runtime
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

Policy:

```text
$MEM / &MEM / #MEM are temporary fast spaces
they are not the default canonical state backend
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

Invalid results:

```text
ok
error
[result: 42]
[ok: 123]
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

Example:

```text
#SYSTEM:error:log:0 = "2026-03-11T12:00:00,OSC:9001:led:1,error,timeout"
```

Log-book declaration:

```text
log <alias> <#target>
```

Example:

```text
log error.log #SYSTEM:error:log
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

Usermodule log expose rule:

```text
usermodules may expose their own logs as readable # targets
```

Examples:

```text
#UM.module:log
#UM.module:error:log
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

Example:

```text
/in/foo/bar 123
-> #OSC:9001:foo:bar = "123"
```

### 17.3 Outbound command

Canonical outbound form:

```text
OSC:<port>:<path...> <value>
```

Example:

```text
OSC:9001:led:1 255
```

Mapping:

```text
OSC:9001:led:1 255
-> send to /out/led/1/ with payload 255
```

Multiple instances may communicate over the same host using different UDP ports.

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

Rules:

```text
#HTTP is protected owning-mechanism space
direct normal assignment to #HTTP:* = syntax error
body may be ""
headers are indexed numerically
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
```

### 18.3 HTTP status policy

```text
HTTP status code is response data, not command execution status
```

Meaning:

```text
HTTP 200 -> [ok] if request executed and output written
HTTP 404 -> [ok] if request executed and output written
HTTP 500 -> [ok] if request executed and output written
transport/runtime failure -> [error: <reason>]
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
```

---

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

#### 19.1.1 List -> table

```text
&list -> #table
```

maps list items into numeric keys.

#### 19.1.2 Table row -> list

```text
#table:row -> &list
```

maps row cells into list items.

#### 19.1.3 Leaf dump rule

A leaf copied into `&` becomes one item.
A leaf copied into `#` becomes one leaf.
A leaf copied into `$` must target `$path:key`.

#### 19.1.4 Direct restrictions

Explicit restriction kept:

```text
# whole table -> & list is not implicitly canonical
```

Whole-table to list requires explicit normalization rule or command support; it is not assumed.

#### 19.1.5 Runtime-space restriction

```text
cp / mv do not apply to ! @ %
```

Meaning:

```text
runtime objects are not canonical copy/move targets
rm still applies to ! @ % according to runtime-object semantics
```

---

### 19.2 Add / Merge Rules

```text
add <target> <source>
```

Add applies only to:

```text
$
#
&
```

Target-specific behavior:

```text
&list
- append only

$node
- target must be a branch / object target
- next key = greatest numeric child key + 1
- if none, start from 0
- if any existing child key is non-numeric -> ERR_TYPE

#table:row
- next key = greatest numeric child key + 1
- if none, start from 0
- if any existing child key is non-numeric -> ERR_TYPE
```

Rules:

```text
add $foo       = valid if $foo is a branch / object target
add $foo:bar   = syntax error
add !...       = syntax error
add @...       = syntax error
add %...       = syntax error
one single-token string is accepted without quotes
quoted single-token string is also valid
multi-token string requires quotes
```

Examples:

```text
add $foo bar
add $foo "bar"
add &jobs "run %worker &worker"
add #table:row $UM.sensor:temp
```

Invalid:

```text
add $foo:bar baz
add %worker something
add !trig something
```

`$CH` is not an indexed list, but `add $CH ...` keeps it behaving as a numerically-growing chat log.

```text
merge <src> <dst>
```

Merge is structural and separate from import.

```text
import = reset + overwrite
merge  = structural combine without reset
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

Examples:

```text
trig !sensor.hot $UM.sensor:temp >= 40
trig !sensor.change onchange $UM.sensor:temp
trig !nightly cron "0 3 * * *"
trig !heartbeat cron "every 1s"
trig !backup cron "daily"
```

Cron input rule:

```text
direct cron spec is allowed
human-readable shorthand is allowed
parser/runtime normalizes shorthand internally
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

State meaning:

```text
0 = inactive / false
1 = active / true
```

Pulse meaning:

```text
pulse = trigger lockout/filter duration in milliseconds
pulse = 0 means no lockout
pulse applies to expr, onchange, and cron
```

Examples:

```text
!sensor.hot:pulse = 100
!sensor.change:pulse = 0
```

### 20.4 Onchange rules

```text
first seen value = baseline only
first seen value does not fire
fire only on actual value change
comparison uses canonical string values
default pulse = 0
pulse on onchange is used only as flood / noise filtering
```

### 20.5 Trigger evaluation policy

```text
declaration syntax errors fail at declaration time
missing or unavailable runtime values do not raise command errors
missing/unavailable runtime values evaluate as non-firing state
```

### 20.6 Trigger lifecycle

```text
trigger names are unique
redefining an existing !name = error: name exists
rm !name is allowed
rm !name removes both definition and runtime state
no residual trigger state remains after rm
```

Write policy:

```text
direct assignment to !<name>:state = syntax error
!<name>:pulse is the writable trigger control field
```

---

## 21. Event Model

Canonical signature:

```text
on !trigger @event "command"
```

Examples:

```text
on !sensor.hot @cooling.start "run &cooling"
on !nightly @backup.run "run &backup"
```

Rules:

```text
event names are unique
redefining an existing @name = error: name exists
rm @name is allowed
rm @name removes both definition and runtime state
one event contains exactly one quoted command payload
direct assignment to @... = syntax error
event fires when its trigger is active according to trigger semantics
```

---

## 22. Runner / Loop Model

### 22.1 % name parsing

Runner names may contain both `.` and `:`.

Allowed % fields:

```text
%<name>:status
%<name>:step
%<name>:mode
%<name>:autostart
```

Parsing rule:

```text
everything between "%" and the final field suffix belongs to the runner name
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

Examples:

```text
%foo:status = run
%foo:status = 0
```

Transition rules:

```text
run is effective only when current status is ok or pause
if current status is stop or error, run must not start execution
stop and error both require explicit recovery to ok or pause before run
```

### 22.3 Step field

```text
%<name>:step accepts only integer values in range 0...N
0 = first step
N = last valid step
step < 0 = invalid
step > N = invalid
```

### 22.4 Mode field

Allowed values:

```text
runonce
pause.first
loop
```

Meaning:

```text
runonce     = normal runner
pause.first = looper default; waits before first execution
loop        = continuous loop mode
```

### 22.5 Autostart field

Allowed values:

```text
off
<integer priority>
```

Meaning:

```text
off              = runner does not boot automatically
0 / 1 / 2 / ...  = runner boots automatically with that priority
smaller number only biases startup order
autostart launch does not wait for earlier autostarts to finish
no meaningful guarantee exists for relative completion order between runners of the same or different priorities
```

Default:

```text
%<name>:autostart = off
```

### 22.6 Write timing

```text
%<name>:mode is writable only when current status != run
%<name>:step is writable only when current status != run
%<name>:autostart is writable only when current status != run
```

### 22.7 Existing-name rule

```text
a new runner/looper instance cannot be created with an existing name
attempting to do so = error: name exists
```

---

## 23. run and loop Signatures

### 23.1 run

Canonical forms:

```text
run "command"
run &list
run %name "command"
run %name &list
```

Meaning:

```text
run "command"   = anonymous direct runonce of one command
run &list       = anonymous direct runonce of a list
run %name "command" = named runonce runner from one command string
run %name &list = named runonce runner from a list
```

Execution rule for named single-command runners:

```text
run %name "command"
- creates a named runonce runner
- runner executes that one command asynchronously
- execution is performed by invoking the canonical parser on that command string
```

Default:

```text
run without explicit mode defaults to mode = runonce
```

### 23.2 loop

Canonical forms:

```text
loop $template
loop #table
loop %name $template
loop %name #table
```

Name derivation:

```text
if %name is omitted, looper name is derived from the source
loop $foo.bar:doo -> %foo.bar:doo
loop #jobs:queue  -> %jobs:queue
```

Default:

```text
loop without explicit mode defaults to mode = pause.first
```

Loop normalization rule:

```text
when a # row is used as one loop step:
- read cells in numeric sorted order
- trim whitespace on each cell
- remove empty values
- join remaining cells with one single space
- the normalized result is one command string
loop output normalizes to &-style ordered steps
```

---

## 24. runonce Terminal Behavior

Successful completion of a named runonce runner:

```text
%<name>:status = ok
%<name>:step   = N
runner remains allocated until explicitly removed
```

Failure of a named runonce runner:

```text
%<name>:status = error
%<name>:step   = failing step
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
```

Rules:

```text
command must be claimed before aliasing
user module writes only to its own namespace
claim.root creates a mapped root view and does not break ownership
```

Example:

```text
claim.root #DMX #UM.DMX
```

Meaning:

```text
#DMX -> #UM.DMX
```

---

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

Qc.<alias>
- explicit output target, module resolved by alias
- output is token[1] after the command token / alias token
```

Q aliases are only for LLM user modules.

LLM is just another user module.

Usermodule ownership:

```text
$UM.<module>:... is writable only by its owning usermodule
other modules may read unless restricted later
normal usermodule writes must not escape their own $UM.<module> namespace
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
source is always resolved from the remaining command-specific input position
```

### File

```text
file = 1 string

export.file
- output is the destination
- source must resolve to one string

import.file
- output is the destination symbol
- output target must resolve to one string slot
```

### JSON

```text
json works with $ & # structures
```

`export.json`:

```text
- source may be $... &... or #...
- source may be single value, list, branch, or multi-level structure
- target may be compatible single value or file
```

`import.json`:

```text
- source may be compatible single value or file
- target may be $... &... or #...
- import = reset + overwrite
- no merge
```

Import target behavior:

```text
target = $
- whole json as one string value

target = &
- list-style import when json fits naturally as one list-like branch / key-value sequence

target = #
- full structured tree / branch import
```

### Code

```text
code root = #...
key   = filename or recursive path
value = code text
# is infinitely recursive by nature
```

Examples:

```text
#code:main.py = "print('hello')"
#code:src:lib:util.py = "def add(a,b): return a+b"
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

Definitions:

```text
ERR_SYNTAX
- grammar / parser error

ERR_EVAL
- expression / evaluation error

ERR_RUNTIME
- valid command, runtime execution failed

ERR_ADAPTER
- external adapter / IO / transport failed

ERR_OWNERSHIP
- ownership / write permission violation

ERR_NOT_FOUND
- source / target / path not found

ERR_TYPE
- incompatible target/source type for command

ERR_STATE
- current object state does not allow operation
```

---

## 28. System Policies

### 28.1 State backend policy

```text
default state backend = SQLite
sqlite is per instance
```

Meaning:

```text
each AIGMos instance owns its own SQLite
shared multi-instance truth should use a server database or another shared-store mechanism
$MEM / &MEM / #MEM are temporary spaces, not the default state store
```

### 28.2 External feed rule

```text
external world never sends canonical commands directly
external integrations write feeds into claimed roots
commands execute only inside the command surface
```

### 28.3 Adapter exposure rule

```text
adapters are exposed as canonical root-prefix spaces
commands operate on symbols / prefixes
commands do not depend on backend implementation names
```

---

## 29. Boot and Autostart Policy

Boot order:

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
runner autostarts are launched with ascending numeric priority bias
autostart launch does not wait for previous autostarts to complete
beyond that bias, no meaningful canonical ordering guarantee exists
```

Meaning:

```text
system inputs come alive before autostarted runners begin consuming them
```

---

## 30. Layout / UI Runtime Model

### 30.1 Canonical UI rule

```text
there is one shared input surface
the active UI target is one layout instance id
```

Meaning:

```text
the renderer never owns module logic
the input loop never targets a module type directly
all UI dispatch goes to the active layout instance
```

Canonical active pointer:

```text
$SYSTEM:layout:active
```

Example:

```text
$SYSTEM:layout:active = q.default
$SYSTEM:layout:active = buffer.main
```

### 30.2 Module type vs instance

```text
module type = exported layout definition / factory
instance    = live runtime object created from that type
```

Canonical rule:

```text
active layout = instance id
not module type name
```

Examples:

```text
module type: q
instances:   q.default, q.coder

module type: buffer
instances:   buffer.main
```

### 30.3 Module type contract

Required exports:

```text
MODULE
TITLE
create_instance(ctx, instance_id, config=None)
```

Meaning:

```text
MODULE = canonical module type name
TITLE  = default human-visible title for that module type
create_instance(...) = factory that returns one live layout instance
```

Optional exports:

```text
CONFIG_SCHEMA
DEFAULT_CONFIG
clone_instance(ctx, src_instance, new_instance_id)
restore_instance(ctx, instance_id, payload)
KEYBINDS
```

Optional-extension rule:

```text
core layout operation must work without any optional exports
optional exports are extensions, not baseline requirements
```

### 30.4 Layout instance contract

Required instance methods:

```text
get_title()
get_prompt()
get_render()
handle_input(line)
```

Optional instance methods:

```text
handle_key(key)
start()
stop()
serialize()
restore(payload)
```

Meaning:

```text
get_title()  -> current visible title
get_prompt() -> current visible prompt
get_render() -> current visible render body
handle_input(line) -> primary line-input handler for the active instance
handle_key(key)    -> optional raw-key handler
start()/stop()     -> optional instance lifecycle hooks
serialize()/restore() -> optional state persistence hooks
```

### 30.5 Input dispatch rule

Canonical flow:

```text
one input line / key stream
→ active layout instance
→ instance decides local handling vs parser passthrough
```

Recommended return contract from `handle_input()` or `handle_key()`:

```text
{"mode":"self"}
{"mode":"cs","line":"<canonical command line>"}
{"mode":"none"}
```

Meaning:

```text
self = instance handled it locally
cs   = pass the returned line to the canonical command parser
none = nothing executed
```

### 30.6 Renderer responsibility

Renderer duties:

```text
1 resolve active instance id
2 read title from the instance
3 read render body from the instance
4 read prompt from the instance
5 draw only those values
```

Renderer must not:

```text
- contain layout-specific business logic
- decide q vs buffer vs planner behavior
- synthesize module-local prompt or title logic
```

### 30.7 State shape for layout instances

Canonical instance-scoped state shape:

```text
$SYSTEM:layout:instances:<id>:module
$SYSTEM:layout:instances:<id>:title
$SYSTEM:layout:instances:<id>:prompt
$SYSTEM:layout:instances:<id>:render
$SYSTEM:layout:instances:<id>:status
$SYSTEM:layout:instances:<id>:dirty
```

Examples:

```text
$SYSTEM:layout:instances:q.default:module = q
$SYSTEM:layout:instances:q.default:title  = Q
$SYSTEM:layout:instances:q.default:prompt = q>
$SYSTEM:layout:instances:q.default:render = ...
```

Meaning:

```text
layout state is instance-scoped
multiple instances of the same module type are first-class
```

### 30.8 Worker model

Canonical rule:

```text
instance may spawn a worker thread if needed
worker thread is optional, not mandatory
```

Meaning:

```text
q.default may have its own worker
q.coder may have its own worker
buffer.main may run without a worker
```

The core rule is:

```text
one shared input surface
many possible layout instances
worker-thread choice is per instance
```

### 30.9 Prompt and title ownership

```text
prompt belongs to the active instance
title belongs to the active instance
```

Meaning:

```text
renderer reads them
renderer does not invent them
```

### 30.10 Key binding policy

Canonical rule:

```text
key bindings may be attached freely to layout modules / instances
but only the active instance may consume its local bindings
```

Precedence:

```text
1 reserved global/system bindings
2 active layout instance bindings
3 raw input fallback
```

Meaning:

```text
inactive layout instances do not consume keys
```

---

## 31. Short Canonical Summary

```text
storage is string-only
execution is explicit
commands return only [ok] or [error: <reason>]
data never returns through command results
OSC is single-message, single-argument, no-bundle
HTTP writes response data into #HTTP:<id>:...
triggers are expr / onchange / cron
events bind one trigger to one quoted command
run accepts:
- "command"
- &list
- %name "command"
- %name &list
loop = pause.first by default
runner fields are :status / :step / :mode / :autostart
add applies only to $ # &
cp / mv do not apply to ! @ %
default state backend is SQLite
MEM is temporary writable memory family
boot order brings OSC/system inputs up before runner autostarts
autostart priority only biases launch order; it does not serialize startup
active layout = instance id
layout module type exports factory
layout instance owns title / prompt / render / input logic
errors append to #SYSTEM:error:log
```
