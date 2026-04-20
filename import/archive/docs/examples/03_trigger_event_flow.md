# 03_trigger_event_flow

Simple trigger/event example.

```text
$SYSTEM:mode = idle
trig !ready $SYSTEM:mode == run
on !ready @start "run %main &boot"

$SYSTEM:mode = run
```

Flow:

1. state changes
2. trigger condition becomes true
3. bound event fires
4. event command starts the runner
