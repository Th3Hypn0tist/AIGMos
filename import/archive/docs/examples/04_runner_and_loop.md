# 04_runner_and_loop

Runner-oriented example.

```text
mk &boot
add &boot "echo init"
add &boot "echo load"
add &boot "echo done"

run %main &boot
```

Typical runner state:

```text
%main:status
%main:step
```

Status model:

- 0 = run
- 1 = ok
- 2 = stop
- 3 = error
- 4 = pause
