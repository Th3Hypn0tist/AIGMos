from __future__ import annotations

import threading
import time
from typing import Any

from system.cs.reporter import write_buffer
from system.cs.runtime_ctx import get_ctx, get_layout_caller_handle, get_runtime, set_runtime
from system.lib.q.errors import QCallError
from system.lib.q.qcue import (
    qcue_claim_next_runnable,
    qcue_complete,
    qcue_lock,
    qcue_runtime,
    qcue_set_started,
    qcue_started,
    qcue_thread_get,
    qcue_thread_set,
    qcue_wake,
    qcue_wake_event,
    qcue_enqueue,
)
from system.lib.q.session import q_chat, qc_raw
from system.lib.q.state import write_text_symbol
from system.state.api import write_value

_RENDER_INTERVAL_SECONDS = 0.12


def alias_from_command_token(command_token: str) -> str:
    return str(command_token.split('.', 1)[1] if '.' in command_token else 'default').strip() or 'default'


def _set_active_live_state(parser, q_root: str, prompt: str, alias: str, *, clear_error: bool = True) -> None:
    clean_root = str(q_root or '').strip()
    clean_alias = str(alias or '').strip()
    if not clean_root:
        return
    write_text_symbol(parser.state, f'{clean_root}:prompt', str(prompt or ''), 'prompt_active_set')
    write_text_symbol(parser.state, f'{clean_root}:status', 'running', 'status_running')
    write_text_symbol(parser.state, f'{clean_root}:response', '', 'response_reset')
    write_text_symbol(parser.state, f'{clean_root}:thinking_text', '', 'thinking_reset')
    write_text_symbol(parser.state, f'{clean_root}:queue_alias', clean_alias, 'queue_alias_active_set')
    if clear_error:
        write_text_symbol(parser.state, f'{clean_root}:error', '', 'error_reset')


def _qc_writer_name(profile_name: str) -> str:
    clean = str(profile_name or 'default').strip() or 'default'
    return f'q:{clean}'


def _write_qc_output(parser, output_symbol: str, payload, profile_name: str) -> None:
    out = write_value(
        parser.state,
        output_symbol,
        payload,
        writer=_qc_writer_name(profile_name),
        op='qc',
    )
    if out.get('error'):
        raise QCallError(str(out['error']))


def _with_runtime_context(parser, caller_handle: str, q_root: str):
    class _Ctx:
        def __enter__(self_nonlocal):
            self_nonlocal.previous = {
                'layout_caller_handle': get_runtime(parser, 'layout_caller_handle', ''),
                'q_state_root': get_runtime(parser, 'q_state_root', ''),
            }
            if caller_handle:
                set_runtime(parser, 'layout_caller_handle', caller_handle)
            if q_root:
                set_runtime(parser, 'q_state_root', q_root)
            return self_nonlocal.previous

        def __exit__(self_nonlocal, exc_type, exc, tb):
            set_runtime(parser, 'layout_caller_handle', self_nonlocal.previous.get('layout_caller_handle', ''))
            set_runtime(parser, 'q_state_root', self_nonlocal.previous.get('q_state_root', ''))
            return False

    return _Ctx()


def _write_qc_success_buffer(parser, caller_handle: str) -> None:
    with _with_runtime_context(parser, caller_handle, ''):
        write_buffer(parser, '[Qc OK!]')


def _render_due(parser, q_root: str, *, interval: float = _RENDER_INTERVAL_SECONDS) -> bool:
    runtime = qcue_runtime(parser)
    ticks = runtime.setdefault('render_tick', {})
    clean_root = str(q_root or '').strip() or '*'
    now = time.monotonic()
    last = float(ticks.get(clean_root, 0.0) or 0.0)
    if (now - last) < max(0.0, float(interval)):
        return False
    ticks[clean_root] = now
    return True


def _mark_q_targets_dirty(parser, q_root: str, *, force: bool = False, full: bool = False) -> None:
    ctx = get_ctx(parser)
    if not isinstance(ctx, dict) or not q_root:
        return
    if (not force) and (not _render_due(parser, q_root)):
        return
    try:
        from system.layout import registry
        from system.layout.lib.editor import mark_dirty
    except Exception:
        parser.force_render = True
        return
    try:
        handles = registry.list_instances(ctx)
    except Exception:
        parser.force_render = True
        return
    marked = 0
    target_view = f'{q_root}:ch'
    for handle in handles:
        try:
            inst = registry.get_instance(ctx, handle)
        except Exception:
            continue
        module_name = str(getattr(inst, 'MODULE', '') or '').strip().lower()
        if module_name not in {'q', 'qmon'}:
            continue
        primary = str(getattr(inst, 'primary_target', '') or '').strip()
        view = str(getattr(inst, 'view_target', '') or '').strip()
        if primary == q_root or view == target_view:
            try:
                mark_dirty(ctx, str(getattr(inst, 'handle', handle) or handle), full=full)
                marked += 1
            except Exception:
                pass
    if marked <= 0:
        parser.force_render = True
        flags = ctx.setdefault('flags', {})
        if isinstance(flags, dict):
            flags['force_render'] = True
            if full:
                flags['layout_hard_redraw'] = True


def _run_q_task(parser, task: dict[str, str]) -> None:
    q_root = str(task.get('q_root') or '')
    task_id = str(task.get('task_id') or '')
    alias = str(task.get('alias') or '')
    prompt = str(task.get('prompt') or '')
    command_token = str(task.get('command_token') or 'q')
    caller_handle = str(task.get('caller_handle') or '')

    def _on_chunk(_chunk: str, _full_text: str, _chat_symbol: str, _key: str) -> None:
        _mark_q_targets_dirty(parser, q_root)

    def _on_done(_full_text: str, _chat_symbol: str, _key: str) -> None:
        _mark_q_targets_dirty(parser, q_root, force=True, full=True)

    _set_active_live_state(parser, q_root, prompt, alias, clear_error=True)
    _mark_q_targets_dirty(parser, q_root, force=True)
    with _with_runtime_context(parser, caller_handle, q_root):
        q_chat(
            parser,
            command_token,
            prompt,
            q_root_override=q_root,
            caller_handle_override=caller_handle or None,
            preinitialized=True,
            queue_meta={
                'alias': alias,
                'q_root': q_root,
                'task_id': task_id,
            },
            on_chunk=_on_chunk,
            on_done=_on_done,
        )


def _run_qc_task(parser, task: dict[str, str]) -> None:
    q_root = str(task.get('q_root') or '')
    task_id = str(task.get('task_id') or '')
    alias = str(task.get('alias') or '')
    prompt = str(task.get('prompt') or '')
    command_token = str(task.get('command_token') or 'qc')
    caller_handle = str(task.get('caller_handle') or '')
    output_symbol = str(task.get('output_symbol') or '')
    if not output_symbol:
        raise QCallError('qc requires output symbol')
    with _with_runtime_context(parser, caller_handle, q_root):
        result = qc_raw(
            parser,
            command_token,
            prompt,
            caller_handle_override=caller_handle or None,
        )
        _write_qc_output(
            parser,
            output_symbol,
            result.get('decoded'),
            str(result.get('profile') or alias_from_command_token(command_token)),
        )
        _write_qc_success_buffer(parser, caller_handle)
    qcue_complete(parser, alias, q_root, task_id, 'done')


def _run_task(parser, task: dict[str, str]) -> None:
    kind = str(task.get('kind') or 'q').strip().lower() or 'q'
    q_root = str(task.get('q_root') or '')
    task_id = str(task.get('task_id') or '')
    alias = str(task.get('alias') or '')
    runtime = qcue_runtime(parser)
    try:
        if kind == 'qc':
            _run_qc_task(parser, task)
        else:
            _run_q_task(parser, task)
    except Exception as exc:
        runtime['last_error'] = f'worker fatal: {exc}'
        if q_root:
            try:
                write_text_symbol(parser.state, f'{q_root}:error', str(exc or ''), 'q_async_error')
                write_text_symbol(parser.state, f'{q_root}:status', 'error', 'q_async_error_status')
            except Exception:
                pass
        try:
            qcue_complete(parser, alias, q_root, task_id, 'error', error=str(exc or ''))
        except Exception as cleanup_exc:
            runtime['last_error'] = f'worker cleanup fatal: {cleanup_exc}'
            if q_root:
                try:
                    write_text_symbol(parser.state, f'{q_root}:error', f'worker cleanup fatal: {cleanup_exc}', 'q_async_cleanup_error')
                    write_text_symbol(parser.state, f'{q_root}:status', 'error', 'q_async_cleanup_error_status')
                except Exception:
                    pass
        _mark_q_targets_dirty(parser, q_root, force=True, full=True)
    finally:
        qcue_wake(parser)
        _mark_q_targets_dirty(parser, q_root, force=True, full=True)


def _start_worker(parser, task: dict[str, str]) -> None:
    q_root = str(task.get('q_root') or '')
    task_id = str(task.get('task_id') or '')
    alias = str(task.get('alias') or '')
    try:
        thread = threading.Thread(
            target=_run_task,
            args=(parser, dict(task)),
            name=f"q-worker-{task_id or '?'}",
            daemon=True,
        )
        thread.start()
    except Exception as exc:
        if q_root:
            write_text_symbol(parser.state, f'{q_root}:error', str(exc or ''), 'q_async_start_error')
            write_text_symbol(parser.state, f'{q_root}:status', 'error', 'q_async_start_error_status')
        bookkeeping_error = None
        if alias and task_id:
            try:
                qcue_complete(parser, alias, q_root, task_id, 'error', error=str(exc or ''))
                qcue_wake(parser)
            except Exception as bk_exc:
                bookkeeping_error = bk_exc
        if bookkeeping_error is not None:
            if q_root:
                try:
                    write_text_symbol(parser.state, f'{q_root}:error', f'worker-start bookkeeping error: {bookkeeping_error}', 'q_async_start_bookkeeping_error')
                    write_text_symbol(parser.state, f'{q_root}:status', 'error', 'q_async_start_bookkeeping_error_status')
                except Exception:
                    pass
            raise bookkeeping_error from exc
        raise


def _scheduler_loop(parser) -> None:
    runtime = qcue_runtime(parser)
    wake = qcue_wake_event(parser)
    try:
        while True:
            wake.wait()
            while True:
                wake.clear()
                task = qcue_claim_next_runnable(parser)
                if task is None:
                    break
                try:
                    _start_worker(parser, task)
                except Exception as exc:
                    runtime['last_error'] = str(exc or '')
                    q_root = str(task.get('q_root') or '')
                    alias = str(task.get('alias') or '')
                    task_id = str(task.get('task_id') or '')
                    if q_root:
                        try:
                            write_text_symbol(parser.state, f'{q_root}:error', f'scheduler start error: {exc}', 'q_scheduler_start_error')
                            write_text_symbol(parser.state, f'{q_root}:status', 'error', 'q_scheduler_start_error_status')
                        except Exception:
                            pass
                    if alias and task_id:
                        qcue_complete(parser, alias, q_root, task_id, 'error', error=str(exc or ''))
                    qcue_wake(parser)
                    _mark_q_targets_dirty(parser, q_root, force=True)
                    continue
    except Exception as exc:
        runtime['last_error'] = str(exc or '')
        raise
    finally:
        with qcue_lock(parser):
            qcue_thread_set(parser, None)
            qcue_set_started(parser, False)


def ensure_scheduler(parser) -> None:
    runtime = qcue_runtime(parser)
    thread = threading.Thread(target=_scheduler_loop, args=(parser,), name='q-cue-scheduler', daemon=True)
    with qcue_lock(parser):
        existing = qcue_thread_get(parser)
        if qcue_started(parser) and existing is not None and existing.is_alive():
            return
        qcue_thread_set(parser, None)
        qcue_set_started(parser, False)

    try:
        thread.start()
    except Exception:
        with qcue_lock(parser):
            qcue_thread_set(parser, None)
            qcue_set_started(parser, False)
        raise

    with qcue_lock(parser):
        qcue_thread_set(parser, thread)
        qcue_set_started(parser, True)
        runtime['last_error'] = ''


def enqueue_q_command(parser, command_token: str, q_root: str, prompt: str) -> None:
    alias = alias_from_command_token(command_token)
    qcue_enqueue(
        parser,
        alias,
        command_token,
        q_root,
        prompt,
        kind='q',
        caller_handle=get_layout_caller_handle(parser),
    )
    ensure_scheduler(parser)
    qcue_wake(parser)
    _mark_q_targets_dirty(parser, q_root, force=True, full=True)


def enqueue_qc_command(parser, command_token: str, output_symbol: str, prompt: str) -> None:
    alias = alias_from_command_token(command_token)
    qcue_enqueue(
        parser,
        alias,
        command_token,
        '',
        prompt,
        kind='qc',
        caller_handle=get_layout_caller_handle(parser),
        output_symbol=output_symbol,
    )
    ensure_scheduler(parser)
    qcue_wake(parser)


__all__ = [
    'alias_from_command_token',
    'ensure_scheduler',
    'enqueue_q_command',
    'enqueue_qc_command',
]
