# q Logic

## Locked summary

```text
stream = gate
think = payload-intent
view_thinking = UI-only
```

## 1) stream

- `stream = true`
  - payload uses stream mode
- `stream = false`
  - no stream mode
  - think is effectively ignored in transport behavior

## 2) think

- `think = true`
  - merge `think_payload` into the request payload
- `think = false`
  - merge `nothink_payload` into the request payload

`think` controls payload intent.
It is not a UI flag.

## 3) view_thinking

- `view_thinking = true`
  - show actual thinking text
- `view_thinking = false` and `think = true`
  - show only `[Thinking...]`

`view_thinking` must not:

- change payload construction
- change parser classification
- change stream enable decision

## 4) minimum feedback rule

While a reply is running, show at least:

```text
[Thinking...]
```

## 5) role field examples

```text
|HELP:q:role:stream = true
|HELP:q:role:think = false
|HELP:q:role:view_thinking = true
```
