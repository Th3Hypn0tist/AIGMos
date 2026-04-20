# Ownership Regression Tests v1

This suite locks the runtime ownership rules into tests.

## Covered guards

- `append_numeric_value()` must use the atomic append path only.
- `ops.py` subtree helpers must preserve explicit writer tags.
- `clear_instance_meta()` must delete with `layout:<handle>` ownership.
- OSC boundary remains documented as `#OSC` + MEM landing zone only.
- Renderer remains documented as read-only.
- Q boundary remains documented as transient live owner vs durable `qcall` owner.

## Files

- `tests/test_ownership_append_atomicity.py`
- `tests/test_ownership_ops_writer_preservation.py`
- `tests/test_ownership_layout_cleanup_writer.py`
- `tests/test_ownership_docs_osc_boundary.py`
- `tests/test_ownership_docs_renderer_no_write.py`
- `tests/test_ownership_docs_q_boundary.py`
