# system/topics/runner.py
#
# Background Runner + trigger bus
#
# Two run modes:
#   1) run <cmd...>                 (single-shot, blocking, NO trigger)
#   2) run %name <target|cmd...>    (background runner, HAS %name.trg)
#
# Targets for run %name:
#   - &routine     (multi-step snapshot)
#   - $sub:key     (single leaf command line)
#   - #a:b:c       (leaf command line)
#   - otherwise:   treat remaining tokens as literal command line
#
# Trigger:
#   %name.trg numeric only
#     0 idle/running/paused
#     1 success pulse (100ms) -> 0
#     2 error   pulse (100ms) -> 0
#     3 stop    pulse (100ms) -> 0
#
# Locks:
#   If runner executes &R, &R is locked against mutations while running/paused.

import time
import threading

ROUTINES_ROOT = "routines"
TEXTS_ROOT = "texts"

PULSE_SEC = 0.100  # 100ms


class RunnerJob:
    def __init__(self, name: str):
        self.name = name            # without leading %
        self.status = "idle"        # idle|running|paused|stopped|failed|done
        self.step_i = 0
        self.last_error = None
        self.log = []
        self.stop_requested = False
        self.paused = False
        self._pause_evt = threading.Event()
        self._pause_evt.set()       # unpaused
        self.trg = 0                # 0/1/2/3


def _parse_pct(tok: str) -> str:
    if not tok.startswith("%"):
        raise ValueError("Expected %name")
    return tok[1:]


def expand_runner_trg(core, parts):
    # Expand tokens like: %name.trg -> "0|1|2|3"
    out = []
    changed = False
    for p in parts:
        if isinstance(p, str) and p.startswith("%") and p.endswith(".trg"):
            name = p[1:-4]
            job = core.runners.get(name)
            out.append(str(job.trg if job else 0))
            changed = True
        else:
            out.append(p)
    return out if changed else parts


def _pulse(job: RunnerJob, value: int):
    job.trg = int(value)
    time.sleep(PULSE_SEC)
    job.trg = 0


def _wait_if_paused(job: RunnerJob):
    while job.paused and not job.stop_requested:
        job._pause_evt.wait(timeout=0.05)


def _lock_routine(core, routine_tok: str, runner_name: str, state: str):
    core.runner_locks[routine_tok] = {"runner": f"%{runner_name}", "state": state}


def _unlock_routine(core, routine_tok: str):
    core.runner_locks.pop(routine_tok, None)


def _resolve_single_target_to_cmd(core, target_tok: str) -> str:
    # $sub:key -> scalar command line
    if target_tok.startswith("$"):
        body = target_tok[1:]
        if ":" not in body:
            raise ValueError("run $ expects $sub:key")
        sub, key = body.split(":", 1)
        core._require_kv_sub(TEXTS_ROOT, sub)
        return str(core.kvl[TEXTS_ROOT][sub].get(key, "")).strip()

    # #a:b:c -> leaf scalar command line
    if target_tok.startswith("#"):
        from system.lib import tables as tbl
        path = [p for p in target_tok[1:].split(":") if p] if len(target_tok) > 1 else []
        node = tbl.node_get(core.tables, tbl.ROOT, path)
        if isinstance(node, dict):
            raise ValueError("run # expects leaf (scalar), not dict node")
        return ("" if node is None else str(node)).strip()

    raise ValueError("Unsupported single target (expected $sub:key or #leaf)")


def _run_steps_background(core, job: RunnerJob, runner_name: str, steps):
    job.status = "running"
    job.log.append(f"START %{runner_name}")

    try:
        for i, step in enumerate(steps):
            job.step_i = i

            if job.stop_requested:
                job.status = "stopped"
                job.log.append("STOP requested")
                _pulse(job, 3)
                return

            _wait_if_paused(job)
            if job.stop_requested:
                job.status = "stopped"
                job.log.append("STOP requested (after pause)")
                _pulse(job, 3)
                return

            step = str(step).strip()
            if not step:
                continue

            # Per-step counter substitution (1-based)
            # Enables: $prompts.<counter> etc.
            step = step.replace("<counter>", str(i + 1))

            # 1.0 safety: no runner-control commands from inside runner
            if step.startswith("run %") or step.startswith("status %") or step.startswith("pause %") or step.startswith("stop %"):
                raise ValueError("Runner cannot execute runner-control commands")

            out = core.execute(step)
            job.log.append(f"[{i}] {step} -> {out}")
            if isinstance(out, str) and out.startswith("Error:"):
                raise ValueError(out)

        job.status = "done"
        job.log.append("DONE")
        _pulse(job, 1)

    except Exception as e:
        job.status = "failed"
        job.last_error = str(e)
        job.log.append(f"FAILED: {e}")
        _pulse(job, 2)

    finally:
        job.paused = False
        job._pause_evt.set()


def run(core, *args):
    """sys.run

    Two modes:
      1) run <cmd...>                 (single-shot, blocking, no trigger)
      2) run %name <target|cmd...>    (background runner, trigger)
    """
    if not args:
        raise ValueError("run expects arguments")

    # background runner mode
    if str(args[0]).startswith("%"):
        name = _parse_pct(str(args[0]))

        if name in core.runners and core.runners[name].status in ("running", "paused"):
            raise ValueError("Runner already active")

        # overwrite job (Option A) + trg reset
        job = RunnerJob(name)
        core.runners[name] = job
        job.trg = 0

        # Convenience: run %name with no explicit target defaults to &<name>
        # (matches the common case: routine name == runner name)
        if len(args) < 2:
            target = f"&{name}"
        else:
            target = str(args[1])
        routine_tok = None

        # resolve steps
        if target.startswith("&"):
            routine_tok = target
            routine_name = target[1:]
            core._require_list_sub(ROUTINES_ROOT, routine_name)
            steps = list(core.l[ROUTINES_ROOT][routine_name])  # SNAPSHOT
            _lock_routine(core, routine_tok, name, "running")

        elif target.startswith("$") or target.startswith("#"):
            cmdline = _resolve_single_target_to_cmd(core, target)
            steps = [cmdline] if cmdline else []

        else:
            # treat remaining tokens as literal command line
            cmdline = " ".join(str(x) for x in args[1:])
            steps = [cmdline] if cmdline.strip() else []

        def worker():
            try:
                _run_steps_background(core, job, name, steps)
            finally:
                if routine_tok:
                    _unlock_routine(core, routine_tok)

        t = threading.Thread(target=worker, name=f"runner:{name}", daemon=True)
        t.start()
        return "OK"

    # single-shot (no trigger)
    cmdline = " ".join(str(x) for x in args)
    return core.execute(cmdline)


def status(core, name_tok):
    name = _parse_pct(str(name_tok))
    job = core.runners.get(name)
    if not job:
        return "NOT_FOUND"
    return f"{job.status} step={job.step_i} err={job.last_error or ''} trg={job.trg}"


def pause(core, name_tok):
    name = _parse_pct(str(name_tok))
    job = core.runners.get(name)
    if not job:
        raise ValueError("Runner not found")

    if job.status == "running":
        job.status = "paused"
        job.paused = True
        job._pause_evt.clear()
        # reflect lock state for error messages
        for k, v in list(core.runner_locks.items()):
            if v.get("runner") == f"%{name}":
                v["state"] = "paused"
        return "OK"

    if job.status == "paused":
        # toggle unpause
        job.status = "running"
        job.paused = False
        job._pause_evt.set()
        for k, v in list(core.runner_locks.items()):
            if v.get("runner") == f"%{name}":
                v["state"] = "running"
        return "OK"

    raise ValueError("pause only valid for running/paused")


def stop(core, name_tok):
    name = _parse_pct(str(name_tok))
    job = core.runners.get(name)
    if not job:
        raise ValueError("Runner not found")

    if job.status in ("running", "paused"):
        job.stop_requested = True
        job.paused = False
        job._pause_evt.set()
        return "OK"

    return "OK"


COMMANDS = {
    "sys.run":    (run,    "Run single command or start background runner", "sys.run <cmd...> | sys.run %<name> <target|cmd...>"),
    "sys.status": (status, "Runner status",                                 "sys.status %<name>"),
    "sys.pause":  (pause,  "Toggle runner pause",                           "sys.pause %<name>"),
    "sys.stop":   (stop,   "Stop runner (graceful)",                        "sys.stop %<name>"),
}
