from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from queue import Queue
from typing import Any

from system.extensions import (
    active_command_is_extension,
    assert_extension_symbol_read_allowed,
    assert_extension_symbol_write_allowed,
)


@dataclass
class StateEnvelope:
    value: Any
    exists: bool
    mono_ns: int
    write_id: int
    writer: str
    op: str


@dataclass
class _Job:
    method: str
    args: tuple[Any, ...]
    done: threading.Event
    out: Any = None


@dataclass
class _FlushJob:
    symbol: str
    envelope: StateEnvelope


class StateEngine:
    """
    Centralized state choke point.

    Reads are served from a live cache. Mutations update the live cache immediately,
    then flow through a FIFO persistence buffer handled by a single flush thread.
    This keeps SQLite as a persistence sink instead of a live streaming buffer.
    """

    def __init__(self, inner, *, flush_batch_limit: int = 256) -> None:
        self._inner = inner
        self._queue: Queue[_Job | None] = Queue()
        self._flush_queue: Queue[_FlushJob | None] = Queue()
        self._closed = False
        self._worker_ident: int | None = None
        self._version_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._flush_cond = threading.Condition()
        self._write_counter = 0
        self._cache: dict[str, StateEnvelope] = {}
        self._dirty: set[str] = set()
        self._flush_batch_limit = max(1, int(flush_batch_limit or 256))
        self._last_flushed_seq = 0
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="aigmos-state-engine",
        )
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="aigmos-state-flush",
        )
        self._thread.start()
        self._flush_thread.start()

    # ------------------------------------------------------------------
    # worker / dispatch
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        self._worker_ident = threading.get_ident()
        while True:
            job = self._queue.get()
            if job is None:
                break
            try:
                fn = getattr(self, f"_do_{job.method}")
            except AttributeError:
                job.out = {"error": f"state method missing: {job.method}", "result": None}
                job.done.set()
                continue
            try:
                job.out = fn(*job.args)
            except Exception as exc:  # pragma: no cover
                job.out = {"error": str(exc), "result": None}
            job.done.set()

    def _submit(self, method: str, *args: Any) -> dict[str, Any]:
        if self._closed:
            return {"error": "state engine closed", "result": None}

        if threading.get_ident() == self._worker_ident:
            fn = getattr(self, f"_do_{method}")
            return fn(*args)

        done = threading.Event()
        job = _Job(method=method, args=args, done=done)
        self._queue.put(job)
        done.wait()
        out = job.out
        return out if isinstance(out, dict) else {"error": "state engine failed", "result": None}

    # ------------------------------------------------------------------
    # metadata helpers
    # ------------------------------------------------------------------

    def _next_meta(self, writer: str, op: str) -> tuple[int, int]:
        with self._version_lock:
            self._write_counter += 1
            return time.monotonic_ns(), self._write_counter

    def _mark_flushed(self, seq: int) -> None:
        with self._flush_cond:
            if seq > self._last_flushed_seq:
                self._last_flushed_seq = seq
            self._flush_cond.notify_all()

    def _inner_result(self, method: str, *args: Any) -> Any:
        fn = getattr(self._inner, method)
        out = fn(*args)
        if isinstance(out, dict):
            if out.get("error"):
                raise ValueError(str(out["error"]))
            return out.get("result")
        return out

    def _load_live_envelope(self, symbol: str) -> StateEnvelope:
        with self._cache_lock:
            cached = self._cache.get(symbol)
            if cached is not None:
                return cached

        value = self._inner_result("get", symbol)
        env = StateEnvelope(
            value=value,
            exists=value is not None,
            mono_ns=0,
            write_id=0,
            writer="bootstrap",
            op="load",
        )
        with self._cache_lock:
            self._cache[symbol] = env
        return env

    def _store_envelope(self, symbol: str, env: StateEnvelope) -> None:
        with self._cache_lock:
            self._cache[symbol] = env
            self._dirty.add(symbol)

    def _enqueue_persist(self, symbol: str, env: StateEnvelope) -> None:
        self._flush_queue.put(_FlushJob(symbol=symbol, envelope=env))

    def _flush_one(self, symbol: str, env: StateEnvelope) -> None:
        if env.exists:
            self._inner_result("set", symbol, env.value)
        else:
            self._inner_result("delete", symbol)

    def _drain_flush_batch(self, first: _FlushJob) -> list[_FlushJob]:
        batch = [first]
        while len(batch) < self._flush_batch_limit:
            try:
                item = self._flush_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                # put sentinel back for outer loop to consume after batch
                self._flush_queue.put(None)
                break
            batch.append(item)
        return batch

    def _coalesce_flush_batch(self, batch: list[_FlushJob]) -> list[_FlushJob]:
        latest: dict[str, _FlushJob] = {}
        order: list[str] = []
        for item in batch:
            if item.symbol not in latest:
                order.append(item.symbol)
            latest[item.symbol] = item
        return [latest[symbol] for symbol in order]

    def _flush_loop(self) -> None:
        while True:
            item = self._flush_queue.get()
            if item is None:
                break
            batch = self._drain_flush_batch(item)
            max_seq = 0
            for flush_item in self._coalesce_flush_batch(batch):
                self._flush_one(flush_item.symbol, flush_item.envelope)
                if flush_item.envelope.write_id > max_seq:
                    max_seq = flush_item.envelope.write_id
            if max_seq:
                self._mark_flushed(max_seq)

    # ------------------------------------------------------------------
    # public api
    # ------------------------------------------------------------------

    def read_state(self, symbol: str) -> dict[str, Any]:
        try:
            assert_extension_symbol_read_allowed(self, symbol)
        except Exception as exc:
            return {"error": str(exc), "result": None}
        return self._submit("read_state", symbol)

    def write_state(self, symbol: str, value: Any, *, writer: str = "system", op: str = "set") -> dict[str, Any]:
        try:
            assert_extension_symbol_write_allowed(self, symbol)
        except Exception as exc:
            return {"error": str(exc), "result": None}
        return self._submit("write_state", symbol, value, str(writer or "system"), str(op or "set"))

    def delete_state(self, symbol: str, *, writer: str = "system", op: str = "delete") -> dict[str, Any]:
        try:
            assert_extension_symbol_write_allowed(self, symbol)
        except Exception as exc:
            return {"error": str(exc), "result": None}
        return self._submit("delete_state", symbol, str(writer or "system"), str(op or "delete"))

    def append_numeric(self, symbol: str, value: Any, *, writer: str = "system", op: str = "append") -> dict[str, Any]:
        try:
            assert_extension_symbol_write_allowed(self, symbol)
        except Exception as exc:
            return {"error": str(exc), "result": None}
        return self._submit("append_numeric", symbol, value, str(writer or "system"), str(op or "append"))

    def list_symbols(self) -> dict[str, Any]:
        out = self._submit("list_symbols")
        if out.get("error"):
            return out
        if active_command_is_extension(self):
            out["result"] = [
                symbol
                for symbol in (out.get("result") or [])
                if not str(symbol).startswith(("$SYSTEM", "#SYSTEM"))
            ]
        return out

    def register_route(self, prefix: str, adapter: Any) -> dict[str, Any]:
        return self._do_register_route(prefix, adapter)

    def unregister_route(self, prefix: str) -> dict[str, Any]:
        return self._do_unregister_route(prefix)

    def snapshot(self) -> dict[str, Any]:
        out = self._submit("snapshot")
        if out.get("error"):
            return out
        if active_command_is_extension(self):
            payload = {}
            for symbol, value in dict(out.get("result") or {}).items():
                if str(symbol).startswith(("$SYSTEM", "#SYSTEM")):
                    continue
                payload[str(symbol)] = value
            out["result"] = payload
        return out

    def consume_dirty(self) -> dict[str, Any]:
        return self._submit("consume_dirty")

    def flush_now(self) -> dict[str, Any]:
        return self._submit("flush_now")

    def close(self) -> None:
        if self._closed:
            return
        self.flush_now()
        self._closed = True
        self._queue.put(None)
        self._flush_queue.put(None)
        self._thread.join(timeout=1.0)
        self._flush_thread.join(timeout=2.0)

    # alias methods
    def get(self, symbol: str) -> dict[str, Any]:
        return self.read_state(symbol)

    def set(self, symbol: str, value: Any) -> dict[str, Any]:
        return self.write_state(symbol, value, writer="alias", op="set")

    def delete(self, symbol: str) -> dict[str, Any]:
        return self.delete_state(symbol, writer="alias", op="delete")

    def remove(self, symbol: str) -> dict[str, Any]:
        return self.delete(symbol)

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    # ------------------------------------------------------------------
    # worker impl
    # ------------------------------------------------------------------

    def _do_read_state(self, symbol: str) -> dict[str, Any]:
        env = self._load_live_envelope(symbol)
        return {"error": "", "result": env.value if env.exists else None}

    def _do_write_state(self, symbol: str, value: Any, writer: str, op: str) -> dict[str, Any]:
        mono_ns, write_id = self._next_meta(writer, op)
        env = StateEnvelope(
            value=value,
            exists=True,
            mono_ns=mono_ns,
            write_id=write_id,
            writer=writer,
            op=op,
        )
        self._store_envelope(symbol, env)
        self._enqueue_persist(symbol, env)
        return {"error": "", "result": value}

    def _do_delete_state(self, symbol: str, writer: str, op: str) -> dict[str, Any]:
        mono_ns, write_id = self._next_meta(writer, op)
        env = StateEnvelope(
            value=None,
            exists=False,
            mono_ns=mono_ns,
            write_id=write_id,
            writer=writer,
            op=op,
        )
        self._store_envelope(symbol, env)
        self._enqueue_persist(symbol, env)
        return {"error": "", "result": None}

    def _do_append_numeric(self, symbol: str, value: Any, writer: str, op: str) -> dict[str, Any]:
        env = self._load_live_envelope(symbol)
        current = env.value if env.exists else None
        text = "" if value is None else str(value)

        if current is None:
            payload: Any = {"0": text}
        elif isinstance(current, dict):
            payload = dict(current)
            next_index = -1
            for key in payload.keys():
                try:
                    next_index = max(next_index, int(str(key)))
                except Exception:
                    continue
            payload[str(next_index + 1)] = text
        elif isinstance(current, list):
            payload = list(current)
            payload.append(text)
        elif isinstance(current, str):
            payload = current + ("\n" if current and text else "") + text
        else:
            payload = {"0": text}

        return self._do_write_state(symbol, payload, writer, op)

    def _do_list_symbols(self) -> dict[str, Any]:
        symbols = set(self._inner_result("list_symbols") or [])
        with self._cache_lock:
            for symbol, env in self._cache.items():
                if env.exists:
                    symbols.add(symbol)
                else:
                    symbols.discard(symbol)
        return {"error": "", "result": sorted(symbols)}

    def _do_register_route(self, prefix: str, adapter: Any) -> dict[str, Any]:
        self._inner_result("register_route", prefix, adapter)
        return {"error": "", "result": prefix}

    def _do_unregister_route(self, prefix: str) -> dict[str, Any]:
        fn = getattr(self._inner, "unregister_route", None)
        if callable(fn):
            out = fn(prefix)
            if isinstance(out, dict) and out.get("error"):
                return {"error": str(out["error"]), "result": None}
        return {"error": "", "result": prefix}

    def _do_snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for symbol in self._do_list_symbols()["result"]:
            payload[symbol] = self._do_read_state(symbol)["result"]
        return {"error": "", "result": payload}

    def _do_consume_dirty(self) -> dict[str, Any]:
        with self._cache_lock:
            dirty = sorted(self._dirty)
            self._dirty.clear()
            payload = {}
            for symbol in dirty:
                env = self._cache.get(symbol)
                payload[symbol] = env.value if (env and env.exists) else None
        return {"error": "", "result": payload}

    def _do_flush_now(self) -> dict[str, Any]:
        with self._version_lock:
            target = self._write_counter
        if target <= self._last_flushed_seq:
            return {"error": "", "result": self._last_flushed_seq}
        deadline = time.time() + 5.0
        with self._flush_cond:
            while self._last_flushed_seq < target:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self._flush_cond.wait(timeout=remaining)
        return {"error": "", "result": self._last_flushed_seq}
