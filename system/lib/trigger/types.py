from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRIGGER_KIND_EXPR = 'expr'
TRIGGER_KIND_ONCHANGE = 'onchange'
TRIGGER_KIND_CRON = 'cron'

TRIGGER_FIELD_STATE = 'state'
TRIGGER_FIELD_PULSE = 'pulse'
ALLOWED_TRIGGER_FIELDS = (TRIGGER_FIELD_STATE, TRIGGER_FIELD_PULSE)


@dataclass(slots=True)
class TriggerDef:
    name: str
    kind: str
    expr: str = ''
    source: str = ''
    cron_spec: str = ''
    pulse_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            'kind': str(self.kind),
            'expr': str(self.expr or ''),
            'source': str(self.source or ''),
            'cron_spec': str(self.cron_spec or ''),
            'pulse_ms': int(self.pulse_ms or 0),
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> 'TriggerDef':
        return cls(
            name=str(name),
            kind=str(data.get('kind') or ''),
            expr=str(data.get('expr') or ''),
            source=str(data.get('source') or ''),
            cron_spec=str(data.get('cron_spec') or ''),
            pulse_ms=_coerce_int(data.get('pulse_ms'), default=0),
        )


@dataclass(slots=True)
class TriggerState:
    state: str = '0'
    pulse_ms: int = 0
    last_fire_ms: int = 0
    baseline_set: str = '0'
    baseline_value: str = ''
    last_value: str = ''
    last_cron_tick: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'state': '1' if str(self.state) == '1' else '0',
            'pulse_ms': int(self.pulse_ms or 0),
            'last_fire_ms': int(self.last_fire_ms or 0),
            'baseline_set': '1' if str(self.baseline_set) == '1' else '0',
            'baseline_value': str(self.baseline_value or ''),
            'last_value': str(self.last_value or ''),
            'last_cron_tick': str(self.last_cron_tick or ''),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> 'TriggerState':
        data = data if isinstance(data, dict) else {}
        return cls(
            state='1' if str(data.get('state') or '0') == '1' else '0',
            pulse_ms=_coerce_int(data.get('pulse_ms'), default=0),
            last_fire_ms=_coerce_int(data.get('last_fire_ms'), default=0),
            baseline_set='1' if str(data.get('baseline_set') or '0') == '1' else '0',
            baseline_value=str(data.get('baseline_value') or ''),
            last_value=str(data.get('last_value') or ''),
            last_cron_tick=str(data.get('last_cron_tick') or ''),
        )


@dataclass(slots=True)
class EventDef:
    name: str
    trigger_name: str
    command: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'trigger': str(self.trigger_name or ''),
            'command': str(self.command or ''),
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> 'EventDef':
        return cls(
            name=str(name),
            trigger_name=str(data.get('trigger') or ''),
            command=str(data.get('command') or ''),
        )


@dataclass(slots=True)
class TriggerEvalResult:
    active: bool = False
    fired: bool = False
    reason: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'active': bool(self.active),
            'fired': bool(self.fired),
            'reason': str(self.reason or ''),
        }


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return int(default)
