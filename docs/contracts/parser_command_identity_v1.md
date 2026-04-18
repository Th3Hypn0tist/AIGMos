# PARSER_COMMAND_IDENTITY v1

Status: canonical draft
Scope: parser-owned command helper layer

## Purpose

Structural helper paths triggered by parser-owned commands must preserve the originating command identity all the way to the final state mutation.

## Rule

- Command execution owner is always `Parser.parse()`.
- Structural helper calls created by a parser-owned command must retain `parser:<command>` as the writer tag.
- Shared helpers such as subtree copy, move, and remove may not collapse ownership into generic tags.
- `compat` is forbidden for normal command-helper write paths.

## Required writer shape

- `parser:cp`
- `parser:mv`
- `parser:rm`
- `parser:import.file`
- `parser:import.code`
- `parser:export.file`
- `parser:export.code`
- `parser:export.json`

## Parser boundary

The parser keeps the active command writer tag in runtime state during command execution.
Command helper layers must read or receive that identity explicitly rather than inventing a generic fallback.

## Allowed pattern

1. `Parser.parse()` resolves the command.
2. Parser sets active writer tag to `parser:<command>`.
3. Helper layer receives that tag explicitly.
4. Final mutation uses `system.state.api.*` with the same writer tag.

## Forbidden pattern

- helper writes with `compat`
- helper writes with `parser` only
- helper writes with no explicit writer tag
- direct raw `state.set/get/delete` in helper mutation paths

## Acceptance

Parser-command structural mutations are considered correct only when:

- final writer tag still identifies the originating command
- subtree helper calls do not downgrade ownership
- no new helper path introduces `compat`
- all resulting writes still go through `system.state.api.*`
