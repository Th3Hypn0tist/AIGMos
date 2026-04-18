# HTTP / I/O Commands

Current helper commands for simple HTTP transport from the command surface.

## hget

```text
hget <output> <url|symbol>
```

HTTP GET helper

current implementation:
- output first
- url may be literal or symbol
- response text is returned through the command framework

note:
- v40 canonical HTTP surface uses HTTP.GET, not hget

## hpost

```text
hpost <output> <url|symbol> <raw-body...>
```

HTTP POST helper

current implementation:
- output first
- url may be literal or symbol
- body may be one symbol or raw trailing text
- response text is returned through the command framework

note:
- v40 canonical HTTP surface uses HTTP.POST, not hpost
