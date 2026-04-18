# RUNTIME_OWNERSHIP_RULES v1

status = canonical  
scope = AIGMos runtime  
goal = lock write ownership and exception boundaries

## 0. Purpose

```txt
PURPOSE = {
  deterministic_execution = yes
  auditable_write_ownership = yes
  silent_bypass_paths = no
  live_vs_durable_truth_separation = yes
}
```

## 1. Core owners

```txt
STATE_OWNER   = StateEngine
EXEC_OWNER    = Parser
RUNNER_OWNER  = runner.py
TRIGGER_OWNER = TriggerRuntime
EVENT_OWNER   = EventRuntime
LAYOUT_OWNER  = layout registry + instance objects
Q_LIVE_OWNER  = live_packet/live_session
Q_STATE_OWNER = qcall
INPUT_OWNER   = input adapter
RENDER_OWNER  = renderer(read-only)
```

## 2. Global rules

```txt
RULE.1 = "All normal state mutations must go through system.state.api.*"
RULE.2 = "All command execution must go through Parser.parse()"
RULE.3 = "Direct state.set/get/delete is forbidden in runtime and command code"
RULE.4 = "Append-like mutations must use append_numeric_value()/append_numeric() only"
RULE.5 = "Renderer may read state, but may not own or mutate runtime logic"
RULE.6 = "Live runtime truth and durable definition truth must remain separate"
RULE.7 = "Every mutation path must carry a meaningful writer tag"
RULE.8 = "Direct backend writes are forbidden except for explicitly declared input landing zones"
```

## 3. Read / write policy

```txt
READ.policy = {
  read_state()        = allowed
  read_value()        = allowed
  direct backend.get  = forbidden outside adapter-internal code
}

WRITE.policy = {
  write_state()       = allowed
  write_value()       = allowed
  delete_state()      = allowed
  delete_value()      = allowed
  append_numeric()    = allowed
  append_numeric_value() = allowed
  direct state.set    = forbidden
  direct state.delete = forbidden
  direct backend.set/delete = forbidden
}
```

## 4. Execution ownership

```txt
EXEC.rule = {
  CLI commands         -> Parser.parse()
  layout input         -> layout/input.py -> Parser.parse()
  event-triggered cmds -> EventRuntime -> Parser.parse()
  future tool bridges  -> Parser.parse()
}

EXEC.forbidden = {
  runtime component executing command text directly without Parser
}
```

## 5. State ownership

```txt
STATE.rule = {
  StateEngine owns = {
    serialization
    write_ordering
    metadata_envelope
    atomic_append_semantics
  }
}

STATE.metadata = {
  writer
  op
  mono_ns
  write_id
}
```

## 6. Writer tags

```txt
WRITER.good = {
  parser:<command>
  layout:<handle>
  qcall:<profile>
  triggers:<name>
  events:<event>
  runner_store:<runner>
  runner:<runner>
  editor:<handle>
}

WRITER.bad = {
  compat
  parser
  layout
  qcall
  triggers
  events
  runner_store
  editor
}
```

## 7. Append ownership

```txt
APPEND.rule = {
  numeric-history-like writes = atomic_only
  applies_to = {
    buffer_logs
    error_logs
    chat_history
    numeric_row_collections
    timeline_event_history
  }
}

APPEND.forbidden = {
  read -> modify -> write append logic in userland
}
```

## 8. Runner ownership

```txt
RUNNER.rule = {
  runner.py owns = {
    inflight_jobs
    worker_threads
    current_step
    live_status
  }

  runner_store.py owns = {
    saved_runner_definitions
    autostart
    persistent_runner_config
  }
}
```

## 9. Trigger ownership

```txt
TRIGGER.rule = {
  TriggerRuntime owns = {
    in_memory_trigger_definitions
    evaluation_loop
    bus_emission
  }

  public_state_surface    = !name
  durable_definition_root = #SYSTEM:runtime:triggers
}
```

## 10. Event ownership

```txt
EVENT.rule = {
  EventRuntime owns = {
    trigger_event_bindings
    event_command_mappings
    in_memory_indices
  }

  durable_definition_root = #SYSTEM:runtime:events
  execution_owner         = Parser
}
```

## 11. Q ownership

```txt
Q.rule = {
  live_packet/live_session own = {
    transient_stream_state
    inflight_response_assembly
    session_local_live_overlay
  }

  qcall owns durable/public Q state = {
    $Q:ch
    $Q:response
    $Q:thinking
    $Q:role
    profile_scoped_variants
  }
}

Q.forbidden = {
  renderer directly mutating chat history
  live session pretending to be durable chat truth
}
```

## 12. Layout ownership

```txt
LAYOUT.rule = {
  instance_object owns = {
    local_behavior
    local_input_semantics
    module_specific_interaction_logic
  }

  layout_state owns = {
    active_instance_metadata
    render_target_metadata
    persistent_instance_helpers
  }

  renderer owns = paint_only
}

RENDER_TARGET.rule = {
  module_exposes_material = yes
  central_renderer_reads_it = yes
  module_does_not_own_global_render_pipeline = yes
}
```

## 13. Input ownership

```txt
INPUT.rule = {
  inputs_are_not_general_state_owners = yes
  adapter_may_write_only_to_declared_landing_zone = yes
}

INPUT.forbidden = {
  arbitrary_persistent_state_writes
  business_state_mutation_outside_declared_intake_surface
}
```

## 14. Direct backend exception rule

```txt
EXCEPTION.rule = {
  direct_backend_writes_allowed_only_for = explicit_input_landing_zones
}
```

## 15. Compat path policy

```txt
COMPAT.rule = {
  compat = transitional_only
  no_new_compat_paths = yes
  existing_compat_paths = legacy_refactor_bridge_only
}
```

## 16. File-level enforcement

```txt
ENFORCE.state_api = {
  system/layout/state.py
  system/cs/lib/ops.py
  system/cs/lib/qcall.py
  system/runtime/runner_store.py
  system/runtime/triggers.py
  system/runtime/events.py
  parser_command_write_helpers
}

ENFORCE.direct_backend_allowed = {
  adapter_internal_code_only
  explicit_input_landing_paths_only
}
```

## 17. Pass / fail test

```txt
PASS = {
  mutation_path_uses_state_api = yes
  writer_tag_identifies_real_owner = yes
  append_is_atomic = yes
  parser_remains_execution_chokepoint = yes
  input_bypass_is_landing_zone_only = yes
}

FAIL = {
  direct_state.set_delete_in_runtime_code = yes
  userland_append_logic = yes
  generic_compat_writer_in_new_code = yes
  renderer_mutating_business_state = yes
  input_adapter_writing_arbitrary_persistent_symbols = yes
}
```

## 18. Final lock

```txt
LOCK = {
  one_write_path
  one_execution_path
  explicit_exceptions_only
}
```
