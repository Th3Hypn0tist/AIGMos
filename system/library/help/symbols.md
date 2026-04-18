# Symbols and Paths

## Core symbol roots

```text
$  object-like state
#  structured namespace / tree
&  ordered list
!  trigger
@  event
%  runner
|  layout instance / layout runtime root
```

## Path separator

```text
:
```

## Dot rule

`.` is allowed in names.
It is not a generic structural separator.

Examples:

```text
|Q.llama
#ROLES:system:help.role
$foo:bar
@alarm.fire
```

## Important `|` rule

`|` is its own symbol space.
It does not collapse into `$`.
Do not explain `|` as a view over `$`.

## `|` examples

```text
|HELP:meta:title
|HELP:buffer
|HELP:command_history
|HELP:q:role:think
|HELP:q:ch
```

## Assignment examples

```text
|HELP:q:role:stream = true
$foo:bar = baz
#ROLES:system:help.role:title = Help
```
