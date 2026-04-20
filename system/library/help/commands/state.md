# State Commands

Commands for reading, writing, listing, copying, moving, importing, exporting, and deleting state-side symbols.

## add

```text
add <target> <source>
```

append one value to $, #, or & target

rules:
- add applies only to $, #, and &
- & appends one new item
- $ and # append at next numeric child key
- existing non-numeric child keys make add fail
- runtime spaces ! @ % | are not valid add targets

examples:
  add &jobs run
  add $foo bar
  add #table:row $UM.sensor:temp

## cat

```text
cat <target>
```

show one resolved target in readable form

target kinds:
- $ # & -> dump current value
- !name -> show trigger detail
- @name -> show event detail
- |name -> show layout instance detail

notes:
- cat does not accept bare roots: ! @ |

## cp

```text
cp <src> <dst>
```

copy one state-side symbol or subtree

rules:
- cp applies only to state-side symbols
- runtime spaces ! @ % | are not valid cp targets or sources
- same-root subtree copy preserves structure
- # -> $ dumps structured content as one string payload
- $ -> # materializes parsed structured content when possible
- cross-root scalar copy writes one scalar value

## echo

```text
echo <message>
```

write one raw message to buffer output

note:
- convenience helper for local output; does not write state by itself

## export.code

```text
export.code <src> <dst>
```

export code-like content from state to filesystem path or symbol

current implementation:
- src first
- dst last
- src may be $, #, or a code subtree
- dst may be a filesystem path or compatible symbol target

note:
- this help describes the current command implementation

## export.file

```text
export.file <src> <dst>
```

export one resolved string value to filesystem path or symbol

current implementation:
- src first
- dst last
- src must resolve to exactly one string value

note:
- this help describes the current command implementation

## export.json

```text
export.json <src> <dst>
```

export structured state as JSON text

current implementation:
- src first
- dst last
- src may be $, &, or #
- dst may be a file path or compatible symbol target

note:
- this help describes the current command implementation

## get

```text
get <output> <symbol>
```

read one symbol for caller-side result handling

current implementation:
- command accepts an output token and one source symbol
- handler returns the resolved result to the command framework

## import.code

```text
import.code <src> <dst>
```

import one file or directory tree into # code structure

current implementation:
- src first
- dst last
- src may be literal path or symbol containing a path
- dst must be a # root
- existing dst subtree is cleared first

note:
- this help describes the current command implementation

## import.file

```text
import.file <src> <target>
```

import one filesystem file into one symbol target

current implementation:
- src first
- target last
- src may be literal path or symbol containing a path
- target receives file text as one value

note:
- this help describes the current command implementation

## import.json

```text
import.json <input> <output>
```

import JSON text into state structure

current implementation:
- input first
- output last
- input may be a symbol containing JSON text
- output target determines whether result lands in $, &, or #
- import resets and overwrites target content

note:
- this help describes the current command implementation

## import.list

```text
import.list <source> <target>
```

helper: import list-like text into an & target

rules:
- source may be a file path or symbol
- target must be an & list

note:
- import.list is a helper and not part of the v40 locked canonical command surface

## ls

```text
ls [target|prefix*]
```

list roots, direct children, wildcard matches, or selected runtime objects

examples:
  ls
  ls $foo
  ls $foo*
  ls |

notes:
- ls | lists top-level layout instances
- ls ! and ls @ list trigger and event objects

## map.files

```text
map.files #input [$output]
```

create a structure-only file path map from a # subtree

usage:
  map.files #input
  map.files #input $output

rules:
- input must be a # symbol
- optional output must be a $ symbol
- with one argument, result is written directly to buffer
- with two arguments, result is written into $output
- directories end with /
- files do not end with /
- names are preserved exactly
- file contents are not copied

## map.structure

```text
map.structure #input [$output]
```

create a structure-only directory map from a # subtree

usage:
  map.structure #input
  map.structure #input $output

rules:
- input must be a # symbol
- optional output must be a $ symbol
- with one argument, result is written directly to buffer
- with two arguments, result is written into $output
- only directories are shown
- directories end with /
- names are preserved exactly
- file contents are not copied

## mk

```text
mk <target>
```

create an empty state node

rules:
- $ and # create empty dict-like nodes
- & creates an empty list
- runtime spaces ! @ % | are not valid mk targets

## mv

```text
mv <src> <dst>
```

move one state-side symbol or subtree

rules:
- mv applies only to state-side symbols
- runtime spaces ! @ % | are not valid mv targets or sources
- move is copy then remove
- # <-> $ structural conversion rules mirror cp

## rm

```text
rm <target>
```

remove one state symbol, subtree, or runtime object

runtime forms:
- rm !trigger
- rm @event
- rm %runner
- rm |layout

notes:
- rm is the destructive path for runtime objects
- bare runtime handles remove the runtime object itself
- nested runtime paths remove only that runtime subtree/value

## set

```text
set <symbol> <value>
```

write one value to one symbol

rules:
- command first tries json decoding
- fallback is raw string value
- symbol must be a valid writable target
