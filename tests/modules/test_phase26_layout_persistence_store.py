from __future__ import annotations

from pathlib import Path

from system.adapters.registry import build_state_request
from system.adapters.sqlite import SQLiteAdapter
from system.cs.parser import Parser
from system.layout import definitions as layout_definitions
from system.layout import registry as layout_registry
from system.layout import state as layout_state
from system.state.engine import StateEngine


def _build_ctx(db_path: Path):
    state_request, _mem, _extras = build_state_request(SQLiteAdapter(db_path), {})
    state = StateEngine(state_request)
    parser = Parser(state)
    ctx = {
        "state": state,
        "parser": parser,
        "config": {"q": {"default": {}}},
        "flags": {},
    }
    parser.runtime["ctx"] = ctx
    parser.runtime["config"] = ctx["config"]
    setattr(state, "_aigmos_runtime", parser.runtime)
    return ctx


def _close_ctx(ctx) -> None:
    state = ctx.get("state")
    if state is not None:
        state.close()


def test_phase26_q_chat_history_survives_restart(tmp_path: Path):
    db_path = tmp_path / "phase26_q_restart.db"

    ctx = _build_ctx(db_path)
    try:
        layout_registry.bootstrap(ctx)
        layout_registry.create_instance(ctx, "q", "|Q.persist", {"profile": "persist"})
        layout_state.set_value(
            ctx,
            "$Q.persist:ch",
            {"1": {"prompt": "hello", "response": "world", "done": 1}},
        )
        layout_registry.switch_active(ctx, "|Q.persist")
        ctx["state"].flush_now()
    finally:
        _close_ctx(ctx)

    ctx2 = _build_ctx(db_path)
    try:
        layout_registry.bootstrap(ctx2)
        assert layout_registry.has_instance(ctx2, "|Q.persist")
        assert layout_registry.get_active_handle(ctx2) == "|Q.persist"
        assert layout_state.get_value(ctx2, "$Q.persist:ch", None) == {
            "1": {"prompt": "hello", "response": "world", "done": 1}
        }
    finally:
        _close_ctx(ctx2)


def test_phase26_layout_binding_survives_restart(tmp_path: Path):
    db_path = tmp_path / "phase26_layout_restart.db"

    ctx = _build_ctx(db_path)
    try:
        layout_registry.bootstrap(ctx)
        tree = layout_definitions.parse_layout_definition("cs")
        specs = layout_definitions.flatten_module_specs(tree)
        layout_registry.create_layout_binding(ctx, "|TEST", "cs", specs, tree=tree)
        layout_registry.switch_active(ctx, "|TEST")
        ctx["state"].flush_now()
    finally:
        _close_ctx(ctx)

    ctx2 = _build_ctx(db_path)
    try:
        layout_registry.bootstrap(ctx2)
        assert layout_registry.has_layout_binding(ctx2, "|TEST")
        assert layout_registry.get_active_handle(ctx2) == "|TEST"
        modules = layout_registry.get_bound_layout_modules(ctx2, "|TEST")
        assert modules
        assert all(layout_registry.has_instance(ctx2, handle) for handle in modules)
    finally:
        _close_ctx(ctx2)
