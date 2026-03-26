# 02_state_and_commands

Small state-oriented example.

```text
mk $SYSTEM
$SYSTEM:mode = idle
$SYSTEM:name = AIGMos

mk #jobs
#jobs:0:cmd = echo boot
#jobs:1:cmd = echo ready

ls $SYSTEM
cat $SYSTEM:name
cat #jobs:0:cmd
```

What this shows:

- explicit symbolic state
- structured `#` rows/cells
- inspection through `ls` and `cat`
