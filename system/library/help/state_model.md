# State Model

## Main container families

- `$` for object-like key/value state
- `#` for structured namespace trees
- `&` for ordered indexed lists

## Runtime families

- `!` trigger objects
- `@` event objects
- `%` runner objects
- `|` layout instance roots

## Layout persistence rule

`|` is the source of truth for layout instance state.

That includes runtime-facing data such as:

- meta
- buffer
- command_history
- q module runtime under the instance

## Separation rule

Do not mix `|` semantics into `$` semantics.
Do not describe `|` as a derived `$` subtree.

## Practical reading examples

```text
cat |HELP:q
cat |HELP:buffer
cat #ROLES:system:help.role
ls |HELP
```
