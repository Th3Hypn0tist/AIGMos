# RUNTIME_EXCEPTIONS v1

status = canonical  
scope = explicit runtime bypass and exception boundaries  
goal = bound all non-standard mutation paths

## 0. Purpose

```txt
PURPOSE = {
  exceptions_must_be_explicit = yes
  exceptions_must_be_bounded = yes
  generic_bypass_shortcuts = no
  ownership_drift = no
}
```

## 1. Default rule

```txt
DEFAULT = {
  execution_path = Parser.parse()
  write_path     = system.state.api.*
}

NON_DEFAULT = exception_only
```

## 2. Exception policy

```txt
EXCEPTION.rule = {
  allowed_only_if = {
    explicitly_named_in_canonical
    scope_bounded
    ownership_clear
    target_surface_declared
    no_generic_reuse
  }
}

EXCEPTION.forbidden = {
  undocumented_bypass
  convenience_shortcut_bypass
  adapter_reuse_as_general_write_path
}
```

## 3. Current allowed exceptions

```txt
ALLOWED = {
  OSC_input_landing_zone
}
```

## 4. OSC exception

The OSC adapter is the only current direct-write exception. Its declared landing zone is `#OSC`, and that landing zone is MEM-only.

```txt
OSC.rule = {
  class = input_exception
  owner = OSC input adapter
  allowed_direct_write = backend.set()
  allowed_target = #OSC
  backend_scope = MEM_only
  landing_zone = "#OSC"
}
```

## 5. OSC meaning

```txt
OSC.meaning = {
  normal_state_mutation_path = no
  StateEngine_metadata_path  = no
  durable_business_state_owner = no
  input_landing_surface_only = yes
}
```

## 6. OSC allowed behavior

```txt
OSC.allowed = {
  receive_packet
  normalize_address_to_#OSC_path
  write_latest_input_value_to_MEM_landing_zone
  overwrite_input_surface_state
}
```

## 7. OSC forbidden behavior

```txt
OSC.forbidden = {
  direct_write_to_general_persistent_state
  direct_write_to_business_symbols_outside_#OSC
  becoming_generic_runtime_shortcut
  silently_claiming_normal_state_ownership
}
```

## 8. Persistence rule after input

```txt
INPUT_TO_PERSISTENCE.rule = {
  input_first_lands_in_MEM = yes
  persistence_elsewhere_requires = explicit_followup_logic
  followup_logic_must_use = {
    Parser.parse()
    or
    system.state.api.*
  }
}
```

## 9. Adapter boundary

```txt
ADAPTER.rule = {
  adapter_internal_backend_calls = allowed_only_inside_adapter
  adapter_external_general_state_ownership = forbidden
}
```

## 10. Future input adapters

```txt
FUTURE_INPUTS.rule = {
  default_model = OSC_model
  each_adapter_must_declare = {
    landing_zone
    backend_scope
    persistence_policy
  }
}

FUTURE_INPUTS.default = {
  landing_zone_only = yes
  MEM_first = yes
  no_business_state_ownership = yes
}
```

## 11. Renderer non-exception

```txt
RENDERER.rule = {
  renderer_is_not_an_exception_writer = yes
  renderer_write_rights = none
}
```

## 12. Compat non-exception

```txt
COMPAT.rule = {
  compat_is_not_a_runtime_exception_class = yes
  compat_is_transitional_refactor_debt = yes
}
```

## 13. Acceptance check

```txt
PASS = {
  only_documented_exceptions_exist = yes
  OSC_writes_only_to_#OSC = yes
  OSC_backend_scope_is_MEM_only = yes
  non_input_code_does_not_reuse_backend_bypass = yes
}

FAIL = {
  new_direct_backend_write_path_without_doc
  OSC_writing_persistent_business_state
  adapter_used_as_general_mutation_shortcut
}
```

## 14. Final lock

```txt
LOCK = {
  one_default_execution_path = yes
  one_default_write_path = yes
  explicit_exceptions_only = yes
  current_runtime_exception_count = 1
}
```
