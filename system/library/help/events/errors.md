# Event Errors and Misconceptions

## Common mistakes

### Mistake: event = trigger

Wrong.
A trigger causes or gates behavior.
An event is the dispatched command unit.

### Mistake: event = workflow engine

Wrong.
An event is intentionally thin.

### Mistake: event stores all runtime logic

Wrong.
Use commands, runners, or other runtime objects for larger logic.

## Failure behavior

If the dispatched command is invalid, the failure belongs to that command execution path, not to a separate event language.
