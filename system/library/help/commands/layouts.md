# Layout and Control Commands

Commands for layout creation, layout-facing control, and hotkey binding.

## bind

```text
bind alt-1..alt-9|alt-0 <command...>
```

bind one alt hotkey slot to one raw command line

rules:
- allowed slots: alt-1..alt-9 and alt-0
- the bound value is stored exactly as one command line
- global/system bindings still take precedence over local instance bindings

example:
  bind alt-1 |Q

## binds

```text
binds
```

list current alt hotkey bindings

shows alt-1..alt-9 and alt-0 with bound command or [unbound]

## new

```text
new |<instance> /<module-or-layout>
```

create one layout instance or one direct module instance

notes:
- /<name> first tries a layout template under system/library/layout or extensions/layout
- if no template exists, it falls back to direct module creation
- layout runtime state lives in the | symbol space

examples:
  new |Q /q
  new |HELP /help
  new |BUFFER /buffer

## reload

```text
reload [help|roles|role <name>|prompts|routines|layout|config|commands|adapters|inputs|all]
```

reload command

examples:
- reload help
- reload roles
- reload role system/help
- reload prompts
- reload routines
- reload layout
- reload config
- reload commands
- reload adapters
- reload inputs
- reload all

## unbind

```text
unbind alt-1..alt-9|alt-0
```

remove one alt hotkey binding

example:
  unbind alt-1

## /

```text
/help [/cmd] | /time | /greeting | /clear | /health q[.alias] | /exit
```

local slash command surface

subcommands:
- /help [cmd]      list short help or one full help
- /time            print local time to buffer
- /greeting        print greeting
- /clear           clear current layout modules and queue redraw
- /cs              switch active layout to cs template instance
- /q               switch active layout to q template instance
- /monitor[.alias] switch active layout to monitor instance
- /health q[.x]    GET q profile health_url
- /exit            stop app
