from __future__ import annotations

import threading
import time
from datetime import datetime
from queue import Queue
from typing import Any

from system.boot import boot_log
from system.lib.trigger.runtime import run_trigger_cycle
from system.lib.trigger.expr_eval import eval_expr
from system.lib.trigger.lifecycle import create_trigger, remove_trigger
from system.lib.trigger.store import list_trigger_names, load_trigger_def, load_trigger_state, save_trigger_state
from system.lib.trigger.types import TRIGGER_KIND_CRON, TRIGGER_KIND_EXPR, TRIGGER_KIND_ONCHANGE, TriggerDef
from system.lib.trigger.onchange import seed_baseline
from system.state.api import read_value, write_value


def _trigger_writer(name: str) -> str:
    clean = str(name or "").strip()
    return f"triggers:{clean}" if clean else "triggers:unknown"


class TriggerRuntime:
    def __init__(self, state, bus: Queue) -> None:
        self.state = state
        self.bus = bus
        self._lock = threading.RLock()

    def add(self, name: str, left: str, right: str, persist: bool = True) -> None:
        _ = persist
        expr = f"{str(left or '').strip()} == {str(right or '').strip()}"
        create_trigger(self.state, TriggerDef(name=name, kind=TRIGGER_KIND_EXPR, expr=expr))

    def get_def(self, name: str) -> dict[str, str] | None:
        trigger_def = load_trigger_def(self.state, name)
        if trigger_def is None:
            return None
        payload = {
            'kind': trigger_def.kind,
            'expr': trigger_def.expr,
            'source': trigger_def.source,
            'cron_spec': trigger_def.cron_spec,
            'pulse_ms': str(trigger_def.pulse_ms),
        }
        if trigger_def.kind == TRIGGER_KIND_EXPR and '==' in trigger_def.expr:
            left, right = trigger_def.expr.split('==', 1)
            payload['left'] = left.strip()
            payload['right'] = right.strip()
        return payload

    def remove(self, name: str, persist: bool = True) -> bool:
        _ = persist
        return bool(remove_trigger(self.state, name))

    def restore(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        for name, item in data.items():
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(item, dict):
                continue
            if load_trigger_def(self.state, name) is not None:
                continue
            kind = str(item.get('kind') or '').strip()
            if kind in {TRIGGER_KIND_EXPR, TRIGGER_KIND_ONCHANGE, TRIGGER_KIND_CRON}:
                create_trigger(self.state, TriggerDef(
                    name=name,
                    kind=kind,
                    expr=str(item.get('expr') or ''),
                    source=str(item.get('source') or ''),
                    cron_spec=str(item.get('cron_spec') or ''),
                    pulse_ms=int(str(item.get('pulse_ms') or '0').strip() or '0'),
                ))
                continue
            left = str(item.get('left') or '').strip()
            right = str(item.get('right') or '').strip()
            if left and right:
                create_trigger(self.state, TriggerDef(name=name, kind=TRIGGER_KIND_EXPR, expr=f"{left} == {right}"))

    def prime(self) -> None:
        with self._lock:
            for name in list_trigger_names(self.state):
                trigger_def = load_trigger_def(self.state, name)
                if trigger_def is None:
                    continue
                trigger_state = load_trigger_state(self.state, name)
                if trigger_def.kind == TRIGGER_KIND_EXPR:
                    active = bool(eval_expr(trigger_def.expr, self._resolve))
                    trigger_state.state = '1' if active else '0'
                elif trigger_def.kind == TRIGGER_KIND_ONCHANGE:
                    current = self._resolve(trigger_def.source)
                    if current is not None:
                        seed_baseline(trigger_state, current)
                    trigger_state.state = '0'
                elif trigger_def.kind == TRIGGER_KIND_CRON:
                    trigger_state.state = '0'
                save_trigger_state(self.state, name, trigger_state)

    def list_names(self) -> list[str]:
        with self._lock:
            return list_trigger_names(self.state)

    def tick(self) -> None:
        with self._lock:
            fired = run_trigger_cycle(self.state, int(time.time() * 1000), datetime.now())
        for trigger_name in fired:
            self.bus.put(trigger_name)

    def _resolve(self, symbol: str):
        return read_value(self.state, symbol, None)


class TriggerLoop(threading.Thread):
    def __init__(self, runtime: TriggerRuntime, poll_seconds: float = 0.05) -> None:
        super().__init__(daemon=True, name="triggers")
        self.runtime = runtime
        self.poll_seconds = float(poll_seconds)
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        boot_log("[trigger-thread] started")
        while self._running:
            try:
                self.runtime.tick()
            except Exception as exc:
                boot_log(f"[trigger-error] {type(exc).__name__}: {exc}")
            time.sleep(self.poll_seconds)
