# Runtime Commands

Commands related to triggers, events, routines, and runner-style execution.

## cycle

```text
cycle <source>
```

helper: create %name in cycle mode from &, $, or # source

rules:
- accepted sources: &name, $template, #table
- resolved snapshot must contain at least 2 steps
- runner name is derived from the source

note:
- cycle is outside the locked v40 canonical command surface

## emit

```text
emit @event | emit !trigger
```

helper: emit one event directly or push one trigger into the trigger bus

note:
- emit is outside the locked v40 canonical command surface

## loop

```text
loop &name
```

current implementation: create %name in loop mode from one indexed & routine

rules:
- accepts only & sources in this implementation
- snapshot must contain at least 2 steps
- runner name is derived from the & source

note:
- this help describes the current command implementation

## on

```text
on !trigger @event "command"
```

bind one trigger to one named event and one quoted command payload

rules:
- event names must be unique
- payload is exactly one quoted command line
- direct assignment to @... is not allowed
- rm @name removes the event binding

## run

```text
run <command|&source>
```

current implementation: execute one command directly or run one & routine once

rules:
- non-& input is dispatched as one raw command line
- & source is snapshotted and executed once in numeric order
- & routine must contain at least 1 step
- errors include failing step index and command

note:
- this help describes the current command implementation

## trig

```text
trig !name <expr> | trig !name onchange <ref> | trig !name cron "spec"
```

create ! trigger

forms:
  trig !name <expr>
  trig !name onchange <ref>
  trig !name cron "spec"

expr operators:
  == != < <= > >= AND OR XOR NOT

rules:
  - logical expressions using AND / OR / XOR / NOT must be grouped with parentheses
  - first seen onchange value seeds baseline and does not fire
  - writable control field: !name:pulse = <ms>
  - readable runtime field: !name:state

examples:
  trig !sensor.hot $UM.sensor:temp >= 40
  trig !sensor.change onchange $UM.sensor:temp
  trig !heartbeat cron "every 1s"
  trig !backup cron "daily"
  !sensor.hot:pulse = 100
