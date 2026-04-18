# Troubleshooting

This page collects common current-snapshot issues.

---

## 1. `Invalid layout`

Example:

```text
|Q
```

but `|Q` has not been created yet.

Fix:

```text
new |Q /q
```

The correct behavior is an error, not a crash.

---

## 2. `/reload layout` does not seem to update a template

Check all of these:

- did you modify the correct `.tmpl` file?
- is the active instance actually bound to that layout route?
- did the reload rebuild successfully?
- is an older runtime snapshot still active?

Good quick check:

```text
/help reload
```

and then switch away and back to the instance.

---

## 3. Help layout renders strangely

Check:

- `system/library/layout/help.tmpl`
- the instance title via `|:title`
- whether the q state root is resolving to the correct instance

Typical intended creation:

```text
new |HELP /help
```

---

## 4. `q` produces no useful output

Check:

- selected profile exists in `config.json`
- provider endpoint is reachable
- `model` is valid for that provider
- response is not only sitting in live fields while you are reading the wrong view

Useful command:

```text
/health q
```

or:

```text
/health q.qwen
```

---

## 5. `qmon` shows the wrong thing

`qmon` is a read-only q monitor.

Verify the alias/target really points where you think it does.

Examples:

```text
<qmon alias="|Q">
<qmon alias="|HELP">
```

If the target instance does not exist, the monitor cannot show meaningful q state.

---

## 6. A command example in docs does not match runtime

Prefer this priority order:

1. current command implementation in `system/cs/commands/`
2. `README.md`
3. `docs/help/`
4. older spec / canonical files

This repository has moved fast, so older files may reflect earlier phases.
