# Q_OWNERSHIP_BOUNDARY v1

status = canonical  
scope = Q runtime ownership split  
goal = lock transient stream/session ownership away from durable chat ownership

## 0. Purpose

```txt
PURPOSE = {
  separate_live_from_durable = yes
  prevent_renderer_ownership_drift = yes
  keep_q_streaming_transient = yes
  keep_chat_history_public_and_stable = yes
}
```

## 1. Core split

```txt
Q_LIVE_OWNER   = live_packet/live_session
Q_STATE_OWNER  = qcall
Q_RENDER_OWNER = renderer(read-only)
```

## 2. Live ownership

```txt
Q.live = {
  owner = live_packet/live_session
  class = transient_runtime_truth

  owns = {
    inflight_request_state
    stream_assembly
    current_partial_response
    current_partial_thinking
    live_done_flag_until_commit
    session_local_overlay
  }
}
```

## 3. Durable ownership

```txt
Q.durable = {
  owner = qcall
  class = public_durable_truth

  owns = {
    $Q:ch
    $Q:response
    $Q:thinking
    $Q:role
    $Q.<profile>:ch
    $Q.<profile>:response
    $Q.<profile>:thinking
    $q:* sampler_symbols
  }
}
```

## 4. Renderer boundary

```txt
Q.renderer = {
  renderer_may_read_durable_state = yes
  renderer_may_read_live_overlay = yes
  renderer_may_merge_for_display_only = yes

  renderer_may_write_chat_history = no
  renderer_may_claim_session_ownership = no
  renderer_may_commit_stream_chunks = no
}
```

## 5. Commit model

```txt
Q.commit_model = {
  stream_begins_in_live_owner = yes
  partial_chunks_accumulate_in_live_owner = yes
  durable_state_updates_happen_through_qcall = yes
  final_public_truth_lives_in_$Q = yes
}
```

## 6. Execution path

```txt
Q.execution = {
  q_command_path   = Parser.parse()
  q_state_writes   = system.state.api.*
  q_writer_pattern = qcall:<profile>
}
```

## 7. Forbidden patterns

```txt
Q.forbidden = {
  renderer_mutates_$Q = yes
  live_session_pretends_to_be_durable_owner = yes
  durable_chat_history_stored_only_in_live_packet = yes
  direct_backend_write_for_q_state = yes
  generic_q_writer_tag = yes
}
```

## 8. Accepted display overlay

```txt
Q.display_overlay = {
  allowed = yes
  meaning = {
    active_layout_may_show_live_state_before_final_commit
    display_overlay_does_not_change_durable_ownership
    visual_merge_is_not_a_write_path
  }
}
```

## 9. Failure examples

```txt
FAIL = {
  renderer_appends_to_$Q:ch
  live_packet_becomes_only_source_of_truth_after_request
  stream_completion_not_committed_to_qcall_owned_state
  profile_scoped_q_state_written_with_wrong_writer_tag
}
```

## 10. Acceptance check

```txt
PASS = {
  live_packet_live_session_are_transient_only = yes
  qcall_is_durable_owner = yes
  renderer_is_read_only = yes
  q_writes_use_qcall:<profile> = yes
  final_chat_history_lives_in_$Q = yes
}
```

## 11. Final lock

```txt
LOCK = {
  stream_session_truth = transient
  chat_history_truth   = durable
  display_merge        = visual_only
  durable_owner        = qcall
}
```
