from __future__ import annotations

from . import registry
from .terminal import run as run_loop


def bootstrap(ctx) -> None:
    registry.bootstrap(ctx)
