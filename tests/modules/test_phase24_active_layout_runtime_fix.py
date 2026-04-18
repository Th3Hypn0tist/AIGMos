from __future__ import annotations

from system.bootstrap import build_ctx
from system.layout import registry


def test_startup_layout_rebuilds_missing_bound_children_and_returns_cs_instance():
    ctx = build_ctx()
    registry.bootstrap(ctx)

    startup = registry._default_startup_layout_handle()
    modules = registry.get_bound_layout_modules(ctx, startup)
    assert modules

    runtime = registry._runtime(ctx)
    for handle in modules:
        runtime["instances"].pop(handle, None)

    registry._ensure_layout_binding_runtime(ctx, startup)
    rebuilt = registry.get_bound_layout_modules(ctx, startup)
    assert rebuilt
    assert all(registry.has_instance(ctx, handle) for handle in rebuilt)

    instance = registry.get_active_instance(ctx)
    assert getattr(instance, "MODULE", "") == "cs"
