"""Runtime runner live ownership.

This module owns only in-memory runner scheduling and inflight job state.
It does not own durable runner definitions, and it does not own command
execution semantics beyond dispatching step text into the parser executor.

Ownership split:
- runner.py          = live scheduling / inflight / status / step
- runner_store.py    = durable runner definitions / autostart
- parser:<command>   = actual command execution ownership
- runner:<runner>    = reserved identity for future live runner state writes
"""

# system/runtime/runner.py

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from system.boot import boot_log


STATUS_RUN = 0
STATUS_WAIT = 1
STATUS_ERROR = 2

MODE_ONCE = "once"
MODE_CYCLE = "cycle"
MODE_LOOP = "loop"

STATUS_BY_TOKEN = {
    "run": STATUS_RUN,
    "wait": STATUS_WAIT,
    "error": STATUS_ERROR,
}

TOKEN_BY_STATUS = {
    STATUS_RUN: "run",
    STATUS_WAIT: "wait",
    STATUS_ERROR: "error",
}

VALID_MODES = {MODE_ONCE, MODE_CYCLE, MODE_LOOP}
RUNNER_CONTROL_TOKENS = {"run", "wait", "once", "cycle", "loop"}


@dataclass
class JobHandle:
    job_id: str
    runner_name: str
    step_index: int
    future: Future
    cancel_event: threading.Event


@dataclass
class Runner:
    name: str
    source: str
    mode: str
    status: int
    step: int
    len: int
    lines: List[str]
    inflight: Optional[str] = None
    inflight_step: Optional[int] = None
    last_result: Any = None
    last_error: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def view(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "mode": self.mode,
            "status": self.status,
            "status_token": TOKEN_BY_STATUS.get(self.status, "unknown"),
            "step": self.step,
            "len": self.len,
            "inflight": self.inflight,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "autostart": int(self.meta.get("autostart", 0) or 0),
        }


_lock = threading.RLock()

_runners: Dict[str, Runner] = {}
_jobs: Dict[str, JobHandle] = {}

_active: List[str] = []
_active_dirty = True

_worker_thread: Optional[threading.Thread] = None
_worker_stop = threading.Event()

_executor: Optional[ThreadPoolExecutor] = None
_executor_max_workers = 8

_idle_sleep = 0.005

_step_executor: Optional[Callable[..., Any]] = None


def _mark_active_dirty() -> None:
    global _active_dirty
    _active_dirty = True


def _rebuild_active_locked() -> None:
    global _active, _active_dirty
    _active = [
        name
        for name, runner in _runners.items()
        if runner.inflight is not None or runner.status == STATUS_RUN
    ]
    _active_dirty = False


def _make_job_id() -> str:
    return uuid.uuid4().hex


def _default_runner_name(source: str) -> str:
    if not source.startswith("&"):
        raise ValueError(f"source must start with &: {source!r}")
    return "%" + source[1:]


def _initial_status_for_mode(mode: str) -> int:
    if mode == MODE_ONCE:
        return STATUS_RUN
    if mode == MODE_CYCLE:
        return STATUS_WAIT
    if mode == MODE_LOOP:
        return STATUS_RUN
    raise ValueError(f"invalid mode: {mode!r}")


def ensure_worker(
    step_executor: Callable[..., Any],
    *,
    max_workers: int = 8,
    idle_sleep: float = 0.005,
) -> None:
    global _step_executor, _executor, _executor_max_workers, _idle_sleep, _worker_thread

    _step_executor = step_executor
    _executor_max_workers = max_workers
    _idle_sleep = idle_sleep

    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_executor_max_workers,
                thread_name_prefix="aigmos-job",
            )

        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_stop.clear()
            _worker_thread = threading.Thread(
                target=_worker_loop,
                name="aigmos-runner-worker",
                daemon=True,
            )
            _worker_thread.start()
            boot_log("[runner-thread] started")


def shutdown_worker(wait: bool = False) -> None:
    _worker_stop.set()
    if wait and _worker_thread is not None:
        _worker_thread.join(timeout=1.0)
    if _executor is not None:
        _executor.shutdown(wait=wait, cancel_futures=True)


def create_runner(
    *,
    source: str,
    lines: List[str],
    mode: str = MODE_ONCE,
    name: Optional[str] = None,
    status: Optional[int] = None,
    autostart: int = 0,
) -> Dict[str, Any]:
    if mode not in VALID_MODES:
        raise ValueError(f"invalid mode: {mode!r}")

    runner_name = name or _default_runner_name(source)
    snapshot = [str(x) for x in lines]

    with _lock:
        if runner_name in _runners:
            raise ValueError(f"runner already exists: {runner_name}")

        runner_status = _initial_status_for_mode(mode) if status is None else int(status)

        if not snapshot:
            runner = Runner(
                name=runner_name,
                source=source,
                mode=mode,
                status=STATUS_ERROR,
                step=0,
                len=0,
                lines=[],
                last_error="empty routine",
                meta={"autostart": int(autostart or 0)},
            )
            _runners[runner_name] = runner
            _mark_active_dirty()
            return runner.view()

        runner = Runner(
            name=runner_name,
            source=source,
            mode=mode,
            status=runner_status,
            step=0,
            len=len(snapshot),
            lines=snapshot,
            meta={"autostart": int(autostart or 0)},
        )
        _runners[runner_name] = runner
        _mark_active_dirty()
        return runner.view()


def get_runner(name: str) -> Optional[Dict[str, Any]]:
    with _lock:
        runner = _runners.get(name)
        return None if runner is None else runner.view()


def list_runners() -> List[Dict[str, Any]]:
    with _lock:
        return [runner.view() for runner in _runners.values()]


def set_runner_autostart(name: str, autostart: int) -> Dict[str, Any]:
    value = int(autostart)
    if value < 0:
        raise ValueError("autostart must be integer >= 0")

    with _lock:
        runner = _runners.get(name)
        if runner is None:
            raise ValueError(f"runner not found: {name}")
        runner.meta["autostart"] = value
        return runner.view()


def runner_control(name: str, token: str) -> Dict[str, Any]:
    if token == "run":
        return set_runner_status(name, STATUS_RUN)
    if token == "wait":
        return set_runner_status(name, STATUS_WAIT)
    if token in VALID_MODES:
        return set_runner_mode(name, token)
    raise ValueError(f"invalid runner control token: {token!r}")


def set_runner_status(name: str, status: int) -> Dict[str, Any]:
    if status not in TOKEN_BY_STATUS:
        raise ValueError(f"invalid status: {status!r}")

    with _lock:
        runner = _runners.get(name)
        if runner is None:
            raise ValueError(f"runner not found: {name}")

        if runner.status == STATUS_ERROR and status == STATUS_RUN:
            raise ValueError(f"runner in error state: {name}")

        runner.status = status
        _mark_active_dirty()
        return runner.view()


def set_runner_mode(name: str, mode: str) -> Dict[str, Any]:
    if mode not in VALID_MODES:
        raise ValueError(f"invalid mode: {mode!r}")

    with _lock:
        runner = _runners.get(name)
        if runner is None:
            raise ValueError(f"runner not found: {name}")

        runner.mode = mode
        _mark_active_dirty()
        return runner.view()


def rm_runner(name: str) -> bool:
    with _lock:
        runner = _runners.get(name)
        if runner is None:
            return False

        if runner.inflight is None:
            del _runners[name]
            _mark_active_dirty()
            return True

        keep_until = (runner.inflight_step if runner.inflight_step is not None else runner.step) + 1
        runner.lines = runner.lines[:keep_until]
        runner.len = len(runner.lines)
        runner.mode = MODE_ONCE
        runner.meta["remove_after_finish"] = True
        _mark_active_dirty()
        return True


def kill_runner(name: str) -> bool:
    with _lock:
        runner = _runners.get(name)
        if runner is None:
            return False

        job_id = runner.inflight
        if job_id is not None:
            job = _jobs.get(job_id)
            if job is not None:
                job.cancel_event.set()
                job.future.cancel()
                _jobs.pop(job_id, None)

        _runners.pop(name, None)
        _mark_active_dirty()
        return True


def _call_step_executor(raw_line: str, cancel_event: threading.Event) -> Any:
    if _step_executor is None:
        raise RuntimeError("runner worker not initialized: missing step executor")

    fn = _step_executor

    try:
        return fn(raw_line, cancel_event=cancel_event)
    except TypeError:
        return fn(raw_line)


def _job_entry(raw_line: str, cancel_event: threading.Event) -> Any:
    if cancel_event.is_set():
        raise RuntimeError("job cancelled before start")
    return _call_step_executor(raw_line, cancel_event)


def _start_job(runner_name: str, step_index: int, raw_line: str) -> JobHandle:
    if _executor is None:
        raise RuntimeError("executor not initialized")

    cancel_event = threading.Event()
    future = _executor.submit(_job_entry, raw_line, cancel_event)
    return JobHandle(
        job_id=_make_job_id(),
        runner_name=runner_name,
        step_index=step_index,
        future=future,
        cancel_event=cancel_event,
    )


def _poll_job(job_id: str) -> Dict[str, Any]:
    with _lock:
        job = _jobs.get(job_id)

    if job is None:
        return {"state": "error", "error": "job handle missing"}

    if not job.future.done():
        return {"state": "pending"}

    try:
        result = job.future.result()
        return {"state": "done", "result": result}
    except BaseException as exc:
        return {"state": "error", "error": str(exc)}


def _finish_job_locked(runner: Runner, job: JobHandle, polled: Dict[str, Any]) -> None:
    runner.inflight = None
    runner.inflight_step = None
    _jobs.pop(job.job_id, None)

    state = polled["state"]

    if state == "error":
        runner.last_error = polled.get("error")
        runner.status = STATUS_ERROR
        _mark_active_dirty()
        return

    runner.last_result = polled.get("result")
    runner.last_error = None

    runner.step = job.step_index + 1

    if runner.step < runner.len:
        _mark_active_dirty()
        return

    runner.step = 0

    if runner.mode == MODE_ONCE:
        if runner.meta.get("remove_after_finish"):
            _runners.pop(runner.name, None)
            _mark_active_dirty()
            return
        runner.status = STATUS_WAIT
        _mark_active_dirty()
        return

    if runner.mode == MODE_CYCLE:
        runner.status = STATUS_WAIT
        _mark_active_dirty()
        return

    if runner.mode == MODE_LOOP:
        runner.status = STATUS_RUN
        _mark_active_dirty()
        return

    runner.status = STATUS_ERROR
    runner.last_error = f"invalid mode at finalize: {runner.mode!r}"
    _mark_active_dirty()


def _tick_runner(name: str) -> None:
    with _lock:
        runner = _runners.get(name)
        if runner is None:
            return

        if runner.inflight is not None:
            job = _jobs.get(runner.inflight)
            if job is None:
                runner.inflight = None
                runner.inflight_step = None
                runner.status = STATUS_ERROR
                runner.last_error = "missing inflight job"
                _mark_active_dirty()
                return
            job_id = job.job_id
            start_job = None
        else:
            if runner.status != STATUS_RUN:
                return
            if runner.step >= runner.len:
                runner.status = STATUS_ERROR
                runner.last_error = "step out of bounds"
                _mark_active_dirty()
                return
            step_index = runner.step
            raw_line = runner.lines[step_index]
            job_id = None
            start_job = (step_index, raw_line)

    if start_job is not None:
        step_index, raw_line = start_job
        job = _start_job(name, step_index, raw_line)

        with _lock:
            runner = _runners.get(name)
            if runner is None:
                job.cancel_event.set()
                job.future.cancel()
                return

            if runner.inflight is not None:
                job.cancel_event.set()
                job.future.cancel()
                runner.status = STATUS_ERROR
                runner.last_error = "runner already has inflight job"
                _mark_active_dirty()
                return

            _jobs[job.job_id] = job
            runner.inflight = job.job_id
            runner.inflight_step = step_index
            _mark_active_dirty()
        return

    polled = _poll_job(job_id)
    if polled["state"] == "pending":
        return

    with _lock:
        runner = _runners.get(name)
        job = _jobs.get(job_id)

        if job is None:
            return

        if runner is None:
            _jobs.pop(job_id, None)
            return

        _finish_job_locked(runner, job, polled)


def _worker_loop() -> None:
    while not _worker_stop.is_set():
        with _lock:
            active_snapshot = list(_active)

        if not active_snapshot:
            with _lock:
                if _active_dirty:
                    _rebuild_active_locked()
            time.sleep(_idle_sleep)
            continue

        for name in active_snapshot:
            try:
                _tick_runner(name)
            except BaseException as exc:
                with _lock:
                    runner = _runners.get(name)
                    if runner is not None:
                        runner.status = STATUS_ERROR
                        runner.last_error = f"worker exception: {exc}"
                        runner.inflight = None
                        runner.inflight_step = None
                        _mark_active_dirty()

        with _lock:
            if _active_dirty:
                _rebuild_active_locked()

        time.sleep(0.0)
