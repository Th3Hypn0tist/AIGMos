from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class HandlerResponse:
    result: Any = None
    buffer_output: str = ""
    error: str = ""
    force_render: bool = False


@dataclass
class CommandDef:
    command: str
    handler: Callable[..., HandlerResponse]
    help_short: str
    help_full: str
