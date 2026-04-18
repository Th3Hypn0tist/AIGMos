from __future__ import annotations

from typing import Any

from system.lib.trigger.expr_eval import normalize_canonical_value
from system.lib.trigger.types import TriggerEvalResult, TriggerState


def evaluate_onchange(current_value: Any, state: TriggerState) -> TriggerEvalResult:
    if current_value is None:
        state.state = '0'
        return TriggerEvalResult(active=False, fired=False, reason='missing')

    current_text = normalize_canonical_value(current_value)

    if str(state.baseline_set or '0') != '1':
        seed_baseline(state, current_text)
        return TriggerEvalResult(active=False, fired=False, reason='baseline')

    changed = has_changed(state.last_value, current_text)
    state.last_value = current_text
    state.state = '1' if changed else '0'
    return TriggerEvalResult(
        active=changed,
        fired=changed,
        reason='changed' if changed else 'nochange',
    )


def seed_baseline(state: TriggerState, current_value: Any) -> None:
    current_text = normalize_canonical_value(current_value)
    state.baseline_value = current_text
    state.last_value = current_text
    state.baseline_set = '1'
    state.state = '0'


def has_changed(old_value: Any, new_value: Any) -> bool:
    return normalize_canonical_value(old_value) != normalize_canonical_value(new_value)
