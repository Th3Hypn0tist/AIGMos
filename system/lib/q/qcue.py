from __future__ import annotations

from contextlib import nullcontext
from typing import Any
import threading

from system.cs.runtime_ctx import runtime_map
from system.state.api import read_value, write_value


QCUE_ROOT = '#SYSTEM:Qcue'
QCUE_WRITER = 'qcue'
_VALID_STATUSES = {'waiting', 'running', 'done', 'error'}


def _runtime(parser) -> dict[str, Any]:
    rt = runtime_map(parser)
    cue = rt.get('q_cue')
    if isinstance(cue, dict):
        lock = cue.get('lock')
        wake = cue.get('wake')
        if isinstance(lock, threading.RLock().__class__) and isinstance(wake, threading.Event):
            return cue
    cue = {
        'lock': threading.RLock(),
        'wake': threading.Event(),
        'started': False,
        'thread': None,
        'last_error': '',
    }
    rt['q_cue'] = cue
    return cue


def qcue_runtime(parser) -> dict[str, Any]:
    return _runtime(parser)


def qcue_lock(parser):
    return _runtime(parser)['lock']


def qcue_wake(parser) -> None:
    _runtime(parser)['wake'].set()


def qcue_wake_event(parser):
    return _runtime(parser)['wake']


def qcue_started(parser) -> bool:
    return bool(_runtime(parser).get('started'))


def qcue_set_started(parser, value: bool) -> None:
    _runtime(parser)['started'] = bool(value)


def qcue_thread_get(parser):
    return _runtime(parser).get('thread')


def qcue_thread_set(parser, thread) -> None:
    _runtime(parser)['thread'] = thread


def _normalize_status(value: Any, default: str = 'waiting') -> str:
    text = str(value or '').strip().lower()
    return text if text in _VALID_STATUSES else default


def _task_payload(task: Any, *, alias: str = '') -> dict[str, Any]:
    data = dict(task) if isinstance(task, dict) else {}
    out = {
        'task_id': str(data.get('task_id') or ''),
        'q_root': str(data.get('q_root') or ''),
        'prompt': str(data.get('prompt') or ''),
        'status': _normalize_status(data.get('status'), 'waiting'),
    }
    kind = str(data.get('kind') or 'q').strip().lower() or 'q'
    if kind not in {'q', 'qc'}:
        kind = 'q'
    out['kind'] = kind
    command_token = str(data.get('command_token') or '')
    if command_token:
        out['command_token'] = command_token
    clean_alias = str(data.get('alias') or alias or '')
    if clean_alias:
        out['alias'] = clean_alias
    caller_handle = str(data.get('caller_handle') or '')
    if caller_handle:
        out['caller_handle'] = caller_handle
    output_symbol = str(data.get('output_symbol') or '')
    if output_symbol:
        out['output_symbol'] = output_symbol
    error = str(data.get('error') or '')
    if error:
        out['error'] = error
    return out


def _numeric_sort_key(text: Any) -> tuple[int, int | str]:
    key = str(text or '')
    return (0, int(key)) if key.isdigit() else (1, key)


def _task_id_rank(task_id: Any) -> int:
    text = str(task_id or '').strip()
    return int(text) if text.isdigit() else -1


def _sorted_numeric_items(value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, list):
        return [(str(idx), item) for idx, item in enumerate(value)]
    if not isinstance(value, dict):
        return []
    return sorted(((str(key), item) for key, item in value.items()), key=lambda pair: _numeric_sort_key(pair[0]))


def _queue_payload(value: Any, *, alias: str = '') -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for _old_key, item in _sorted_numeric_items(value):
        if not isinstance(item, dict):
            continue
        out[str(len(out))] = _task_payload(item, alias=alias)
    return out


def _history_payload(value: Any, *, alias: str = '') -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, item in _sorted_numeric_items(value):
        if not isinstance(item, dict):
            continue
        payload = _task_payload(item, alias=alias)
        task_id = str(payload.get('task_id') or key or '')
        if not task_id:
            continue
        payload['task_id'] = task_id
        out[task_id] = payload
    return out


def _active_global_payload(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for key, item in value.items():
        q_root = str(key or '').strip()
        if not q_root:
            continue
        alias = ''
        task_id = ''
        if isinstance(item, dict):
            alias = str(item.get('alias') or '').strip()
            task_id = str(item.get('task_id') or '').strip()
        else:
            task_id = str(item or '').strip()
        if not task_id:
            continue
        entry: dict[str, str] = {'task_id': task_id}
        if alias:
            entry['alias'] = alias
        out[q_root] = entry
    return out


def _alias_payload(alias: str, value: Any) -> dict[str, Any]:
    src = dict(value) if isinstance(value, dict) else {}
    return {
        'queue': _queue_payload(src.get('queue'), alias=alias),
        'history': _history_payload(src.get('history'), alias=alias),
    }


def _merge_legacy_alias_active(aliases_raw: dict[str, Any], active_global: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    merged = dict(active_global)
    for raw_alias, raw_value in aliases_raw.items():
        alias = str(raw_alias or '').strip()
        if not alias or not isinstance(raw_value, dict):
            continue
        legacy_active = raw_value.get('active') if isinstance(raw_value.get('active'), dict) else {}
        for q_root, task_id in legacy_active.items():
            clean_root = str(q_root or '').strip()
            clean_task_id = str(task_id or '').strip()
            if not clean_root or not clean_task_id:
                continue
            current = merged.get(clean_root)
            if current is None or _task_id_rank(clean_task_id) >= _task_id_rank(current.get('task_id')):
                merged[clean_root] = {'alias': alias, 'task_id': clean_task_id}
    return _active_global_payload(merged)


def _state_payload(value: Any) -> dict[str, Any]:
    src = dict(value) if isinstance(value, dict) else {}
    try:
        seq = int(src.get('seq') or 0)
    except Exception:
        seq = 0
    aliases_raw = src.get('aliases') if isinstance(src.get('aliases'), dict) else {}
    aliases: dict[str, dict[str, Any]] = {}
    for key, item in aliases_raw.items():
        alias = str(key or '').strip()
        if not alias:
            continue
        aliases[alias] = _alias_payload(alias, item)
    active = _active_global_payload(src.get('active'))
    active = _merge_legacy_alias_active(aliases_raw, active)
    return {
        'seq': max(0, seq),
        'active': active,
        'aliases': aliases,
    }


def _state_from_target(target):
    return getattr(target, 'state', target)


def _lock_for_target(target):
    parser = target if hasattr(target, 'state') else None
    return qcue_lock(parser) if parser is not None else nullcontext()


def qcue_state_get(state) -> dict[str, Any]:
    raw = read_value(state, QCUE_ROOT, {})
    return _state_payload(raw)


def qcue_state_set(state, data: dict[str, Any]) -> dict[str, Any]:
    payload = _state_payload(data)
    out = write_value(state, QCUE_ROOT, payload, writer=QCUE_WRITER, op='qcue_set')
    if out.get('error'):
        raise RuntimeError(str(out.get('error') or 'failed to write #SYSTEM:Qcue'))
    return payload


def _qcue_alias_get_unlocked(data: dict[str, Any], alias: str) -> dict[str, Any]:
    clean = str(alias or '').strip() or 'default'
    aliases = dict(data.get('aliases') or {})
    return _alias_payload(clean, aliases.get(clean))


def _qcue_alias_set_unlocked(data: dict[str, Any], alias: str, alias_data: dict[str, Any]) -> dict[str, Any]:
    clean = str(alias or '').strip() or 'default'
    aliases = dict(data.get('aliases') or {})
    aliases[clean] = _alias_payload(clean, alias_data)
    data['aliases'] = aliases
    return aliases[clean]


def _qcue_active_global_get_unlocked(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    return _active_global_payload(data.get('active'))


def _qcue_active_global_set_unlocked(data: dict[str, Any], active_map: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    payload = _active_global_payload(active_map)
    data['active'] = payload
    return payload


def _qcue_seq_next_unlocked(data: dict[str, Any]) -> str:
    data['seq'] = int(data.get('seq') or 0) + 1
    return str(data['seq'])


def _queue_items(alias_data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(key, dict(item)) for key, item in _sorted_numeric_items(alias_data.get('queue')) if isinstance(item, dict)]


def qcue_alias_get(target, alias: str) -> dict[str, Any]:
    state = _state_from_target(target)
    data = qcue_state_get(state)
    return _qcue_alias_get_unlocked(data, alias)


def qcue_alias_set(target, alias: str, alias_data: dict[str, Any]) -> dict[str, Any]:
    state = _state_from_target(target)
    with _lock_for_target(target):
        data = qcue_state_get(state)
        out = _qcue_alias_set_unlocked(data, alias, alias_data)
        qcue_state_set(state, data)
    return dict(out)


def qcue_active_global_get(target) -> dict[str, dict[str, str]]:
    state = _state_from_target(target)
    data = qcue_state_get(state)
    return _qcue_active_global_get_unlocked(data)


def qcue_active_global_set(target, active_map: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    state = _state_from_target(target)
    with _lock_for_target(target):
        data = qcue_state_get(state)
        out = _qcue_active_global_set_unlocked(data, active_map)
        qcue_state_set(state, data)
    return dict(out)


def qcue_seq_next(target) -> str:
    state = _state_from_target(target)
    with _lock_for_target(target):
        data = qcue_state_get(state)
        task_id = _qcue_seq_next_unlocked(data)
        qcue_state_set(state, data)
    return task_id


def qcue_queue_push(target, alias: str, entry: dict[str, Any]) -> dict[str, Any]:
    state = _state_from_target(target)
    clean_alias = str(alias or '').strip() or 'default'
    payload = _task_payload(entry, alias=clean_alias)
    with _lock_for_target(target):
        data = qcue_state_get(state)
        alias_data = _qcue_alias_get_unlocked(data, clean_alias)
        queue = _queue_payload(alias_data.get('queue'), alias=clean_alias)
        queue[str(len(queue))] = payload
        alias_data['queue'] = queue
        _qcue_alias_set_unlocked(data, clean_alias, alias_data)
        qcue_state_set(state, data)
    return payload


def qcue_queue_pop(target, alias: str, index: str | int | None = None):
    state = _state_from_target(target)
    clean_alias = str(alias or '').strip() or 'default'
    with _lock_for_target(target):
        data = qcue_state_get(state)
        alias_data = _qcue_alias_get_unlocked(data, clean_alias)
        items = _queue_items(alias_data)
        if not items:
            return None
        picked_key = None
        if index is None:
            picked_key = items[0][0]
        else:
            idx_text = str(index)
            for key, _item in items:
                if key == idx_text:
                    picked_key = key
                    break
        if picked_key is None:
            return None
        task = dict((alias_data.get('queue') or {}).get(picked_key) or {})
        queue = dict(alias_data.get('queue') or {})
        queue.pop(picked_key, None)
        alias_data['queue'] = _queue_payload(queue, alias=clean_alias)
        _qcue_alias_set_unlocked(data, clean_alias, alias_data)
        qcue_state_set(state, data)
    return _task_payload(task, alias=clean_alias)


def qcue_enqueue(parser, alias: str, command_token: str, q_root: str, prompt: str, *, kind: str = 'q', caller_handle: str = '', output_symbol: str = '') -> dict[str, Any]:
    clean_alias = str(alias or '').strip() or 'default'
    clean_q_root = str(q_root or '').strip()
    clean_kind = str(kind or 'q').strip().lower() or 'q'
    if clean_kind not in {'q', 'qc'}:
        clean_kind = 'q'
    with qcue_lock(parser):
        data = qcue_state_get(parser.state)
        task_id = _qcue_seq_next_unlocked(data)
        entry = _task_payload({
            'task_id': task_id,
            'alias': clean_alias,
            'q_root': clean_q_root,
            'command_token': str(command_token or ('qc' if clean_kind == 'qc' else 'q')),
            'prompt': str(prompt or ''),
            'status': 'waiting',
            'kind': clean_kind,
            'caller_handle': str(caller_handle or ''),
            'output_symbol': str(output_symbol or ''),
        }, alias=clean_alias)
        alias_data = _qcue_alias_get_unlocked(data, clean_alias)
        queue = _queue_payload(alias_data.get('queue'), alias=clean_alias)
        queue[str(len(queue))] = entry
        alias_data['queue'] = queue
        _qcue_alias_set_unlocked(data, clean_alias, alias_data)
        qcue_state_set(parser.state, data)
    return entry


def qcue_claim_next_runnable(parser) -> dict[str, Any] | None:
    with qcue_lock(parser):
        data = qcue_state_get(parser.state)
        aliases = dict(data.get('aliases') or {})
        active_global = _qcue_active_global_get_unlocked(data)

        def _try_pick(want_kind: str):
            nonlocal data, aliases, active_global
            active_root, _active_alias, active_task_id = _effective_q_active(active_global)
            if want_kind == 'q' and active_task_id:
                return None
            for alias in sorted(aliases.keys()):
                alias_data = _alias_payload(alias, aliases.get(alias))
                queue_items = _queue_items(alias_data)
                picked_key = None
                picked_task = None
                for key, candidate in queue_items:
                    task = _task_payload(candidate, alias=alias)
                    if task.get('status') != 'waiting':
                        continue
                    if str(task.get('kind') or 'q') != want_kind:
                        continue
                    q_root = str(task.get('q_root') or '').strip()
                    if want_kind == 'q':
                        if not q_root:
                            continue
                        if active_root and active_task_id:
                            continue
                    picked_key = key
                    picked_task = task
                    break
                if picked_key is None or picked_task is None:
                    continue
                queue = dict(alias_data.get('queue') or {})
                picked_task['status'] = 'running'
                queue[picked_key] = picked_task
                alias_data['queue'] = _queue_payload(queue, alias=alias)
                _qcue_alias_set_unlocked(data, alias, alias_data)
                if want_kind == 'q':
                    active_global = {}
                    active_global[str(picked_task.get('q_root') or '')] = {
                        'alias': alias,
                        'task_id': str(picked_task.get('task_id') or ''),
                    }
                    _qcue_active_global_set_unlocked(data, active_global)
                qcue_state_set(parser.state, data)
                return dict(picked_task)
            return None

        picked = _try_pick('q')
        if picked is not None:
            return picked
        return _try_pick('qc')


def qcue_complete(parser, alias: str, q_root: str, task_id: str, status: str, *, error: str = '') -> dict[str, Any]:
    clean_alias = str(alias or '').strip() or 'default'
    clean_q_root = str(q_root or '').strip()
    clean_task_id = str(task_id or '').strip()
    clean_status = _normalize_status(status, 'done')
    with qcue_lock(parser):
        data = qcue_state_get(parser.state)
        aliases = dict(data.get('aliases') or {})
        alias_data = _alias_payload(clean_alias, aliases.get(clean_alias))
        queue = dict(alias_data.get('queue') or {})
        history = dict(alias_data.get('history') or {})
        active_global = _qcue_active_global_get_unlocked(data)

        finished = None
        remove_key = None
        for key, item in _queue_items(alias_data):
            payload = _task_payload(item, alias=clean_alias)
            if str(payload.get('task_id') or '') == clean_task_id:
                finished = payload
                remove_key = key
                break
        if finished is None:
            payload = history.get(clean_task_id)
            if isinstance(payload, dict):
                finished = _task_payload(payload, alias=clean_alias)
        if finished is None:
            raise RuntimeError(f'qcue_complete: task not found alias={clean_alias} q_root={clean_q_root} task_id={clean_task_id}')

        finished['status'] = clean_status
        if clean_q_root:
            finished['q_root'] = clean_q_root
        if error:
            finished['error'] = str(error)
        elif 'error' in finished and clean_status != 'error':
            finished.pop('error', None)

        if remove_key is not None:
            queue.pop(remove_key, None)
        alias_data['queue'] = _queue_payload(queue, alias=clean_alias)
        history[clean_task_id] = finished
        alias_data['history'] = _history_payload(history, alias=clean_alias)
        _qcue_alias_set_unlocked(data, clean_alias, alias_data)

        if clean_q_root:
            active_entry = dict(active_global.get(clean_q_root) or {})
            if str(active_entry.get('task_id') or '').strip() == clean_task_id:
                active_global.pop(clean_q_root, None)
        if clean_task_id:
            for root, entry in list(active_global.items()):
                if str((entry or {}).get('task_id') or '').strip() == clean_task_id:
                    active_global.pop(root, None)
        _qcue_active_global_set_unlocked(data, active_global)
        qcue_state_set(parser.state, data)
        return dict(finished)


def _queue_lookup_alias_order(aliases: dict[str, Any], prefer_alias: str, active_alias: str) -> list[str]:
    names = sorted(str(name) for name in aliases.keys())
    ordered: list[str] = []
    for candidate in (prefer_alias, active_alias):
        clean = str(candidate or '').strip()
        if clean and clean in aliases and clean not in ordered:
            ordered.append(clean)
    ordered.extend(name for name in names if name not in ordered)
    return ordered


def _effective_q_active(active_global: dict[str, Any]) -> tuple[str, str, str]:
    best_root = ''
    best_alias = ''
    best_task_id = ''
    best_rank: tuple[int, int | str] | None = None
    for root, raw in dict(active_global or {}).items():
        entry = dict(raw or {})
        task_id = str(entry.get('task_id') or '').strip()
        if not task_id:
            continue
        rank = _task_id_rank(task_id)
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_root = str(root or '').strip()
            best_alias = str(entry.get('alias') or '').strip()
            best_task_id = task_id
    return best_root, best_alias, best_task_id


def qcue_lookup_root(state, q_root: str, prefer_alias: str | None = None) -> dict[str, Any] | None:
    clean_q_root = str(q_root or '').strip()
    if not clean_q_root:
        return None
    prefer = str(prefer_alias or '').strip()
    data = qcue_state_get(state)
    aliases = dict(data.get('aliases') or {})
    active_global = _qcue_active_global_get_unlocked(data)
    active_root, active_alias, active_task_id = _effective_q_active(active_global)
    alias_names = _queue_lookup_alias_order(aliases, prefer, active_alias)

    best_waiting: dict[str, Any] | None = None
    best_waiting_key: tuple[int, int, int, str] | None = None
    history_candidates: list[tuple[tuple[int, int, str], dict[str, Any]]] = []

    for alias_index, alias in enumerate(alias_names):
        alias_data = _alias_payload(alias, aliases.get(alias))
        queue_items = _queue_items(alias_data)
        for pos, (_key, item) in enumerate(queue_items, start=1):
            payload = _task_payload(item, alias=alias)
            if str(payload.get('q_root') or '').strip() != clean_q_root:
                continue
            task_id = str(payload.get('task_id') or '')
            is_active = bool(active_root and clean_q_root == active_root and active_alias and alias == active_alias and active_task_id and task_id == active_task_id)
            payload_status = str(payload.get('status') or 'waiting')
            if not is_active and payload_status == 'running':
                payload_status = 'waiting'
            info = {
                'alias': alias,
                'task_id': task_id,
                'q_root': clean_q_root,
                'status': 'running' if is_active else payload_status,
                'position': pos,
                'queue_total': len(queue_items),
                'prompt': str(payload.get('prompt') or ''),
                'active': is_active,
            }
            if is_active or info['status'] == 'running':
                return info
            waiting_key = (
                0 if alias == prefer and prefer else 1,
                int(pos),
                -_task_id_rank(task_id),
                f'{alias_index:06d}:{alias}',
            )
            if best_waiting_key is None or waiting_key < best_waiting_key:
                best_waiting = info
                best_waiting_key = waiting_key
        history = dict(alias_data.get('history') or {})
        for task_id, item in history.items():
            payload = _task_payload(item, alias=alias)
            if str(payload.get('q_root') or '').strip() != clean_q_root:
                continue
            hist = {
                'alias': alias,
                'task_id': str(payload.get('task_id') or task_id or ''),
                'q_root': clean_q_root,
                'status': str(payload.get('status') or ''),
                'position': None,
                'prompt': str(payload.get('prompt') or ''),
                'active': False,
            }
            history_key = (
                0 if alias == prefer and prefer else 1,
                -_task_id_rank(hist['task_id']),
                f'{alias_index:06d}:{alias}',
            )
            history_candidates.append((history_key, hist))

    if best_waiting is not None:
        return best_waiting
    if history_candidates:
        history_candidates.sort(key=lambda item: item[0])
        return history_candidates[0][1]
    return None


__all__ = [
    'QCUE_ROOT',
    'qcue_runtime',
    'qcue_lock',
    'qcue_wake',
    'qcue_wake_event',
    'qcue_started',
    'qcue_set_started',
    'qcue_thread_get',
    'qcue_thread_set',
    'qcue_state_get',
    'qcue_state_set',
    'qcue_alias_get',
    'qcue_alias_set',
    'qcue_queue_push',
    'qcue_queue_pop',
    'qcue_active_global_get',
    'qcue_active_global_set',
    'qcue_seq_next',
    'qcue_enqueue',
    'qcue_claim_next_runnable',
    'qcue_complete',
    'qcue_lookup_root',
]
