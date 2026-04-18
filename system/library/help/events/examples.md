# Event Examples

## Basic mental model

An event behaves like a command packet that eventually goes through the parser.

## Example shapes

```text
@alarm = echo alarm
@refresh = /reload all
@status = cat |HELP:q
```

## Trigger to event idea

```text
!sensor.hot  -> @cooling.start
```

## Runner to event idea

```text
%poller -> emit @status
```

## Important reminder

The event itself is still just a dispatch unit.
The heavy logic belongs in the command it runs, in triggers, or in runners.
