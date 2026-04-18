from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system.adapters.registry import build_state_request
from system.adapters.sqlite import SQLiteAdapter
from system.cs.commands.ls import handler as ls_handler
from system.cs.parser import Parser
from system.layout import registry as layout_registry
from system.layout import state as layout_state
from system.state.engine import StateEngine


class _EchoHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {}

        message = ""
        if isinstance(payload, dict):
            messages = payload.get("messages") or []
            if isinstance(messages, list) and messages:
                last = messages[-1]
                if isinstance(last, dict):
                    message = str(last.get("content") or "")
            if not message:
                message = str(payload.get("prompt") or payload.get("input") or "")

        data = json.dumps({
            "message": {"content": message},
            "response": message,
            "done": True,
        }).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


def _start_echo_server() -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), _EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, int(server.server_port)


def _build_ctx(tmp_path: Path, *, port: int):
    db_path = tmp_path / "phase24_state.db"
    state_request, _mem, _extras = build_state_request(SQLiteAdapter(db_path), {})
    state = StateEngine(state_request)
    parser = Parser(state)
    ctx = {
        "state": state,
        "parser": parser,
        "config": {
            "q": {
                "default": {
                    "provider": "openai",
                    "base_url": f"http://127.0.0.1:{port}",
                    "api_key": "x",
                    "model": "dummy",
                    "timeout_seconds": 2,
                    "stream": False,
                }
            }
        },
        "flags": {},
    }
    parser.runtime["ctx"] = ctx
    parser.runtime["config"] = ctx["config"]
    setattr(state, "_aigmos_runtime", parser.runtime)
    layout_registry.bootstrap(ctx)
    return ctx


def _close_ctx(ctx) -> None:
    state = ctx.get("state")
    if state is not None:
        state.close()


def _wait_until(predicate, *, timeout: float = 2.0, step: float = 0.05) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return
        time.sleep(step)
    raise AssertionError("timeout waiting for condition")


def test_phase24_startup_cs_template_and_ls(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert layout_registry.get_active_handle(ctx) == "|CS"
        assert layout_registry.has_layout_binding(ctx, "|CS")
        assert not layout_registry.has_layout_binding(ctx, "|Q")
        assert layout_registry.list_instances(ctx) == ["|CS.CS.cs1", "|MONITOR.CS.monitor1"]

        response = ls_handler("ls |", ctx["parser"])
        assert response.error == ""
        assert response.buffer_output.splitlines() == [
            "CS",
            "CS.CS.cs1",
            "MONITOR.CS.monitor1",
        ]

        assert ctx["parser"].parse("ls |") is None
        assert layout_state.get_value(ctx, "|CS:buffer", None) == "CS\nCS.CS.cs1\nMONITOR.CS.monitor1"
    finally:
        _close_ctx(ctx)
        server.shutdown()




def test_phase24_cs_row_renders_visible_material(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        lines, prompt = layout_registry.build_screen(ctx)
        joined = "\n".join(lines)
        assert "[CS[CS]]" in joined or "[CS[|CS]]" in joined or "[CS]" in joined
        assert "cs>" not in joined
        assert prompt == "cs> "
    finally:
        _close_ctx(ctx)
        server.shutdown()

def test_phase24_q_template_instantiation_and_qcs_alias_binding(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert layout_registry.get_active_handle(ctx) == "|Q"
        assert layout_registry.has_layout_binding(ctx, "|Q")
        assert layout_registry.get_bound_layout_modules(ctx, "|Q") == [
            "|Q.Q.q1",
            "|CS.Q.cs1",
            "|MONITOR.Q.monitor1",
        ]

        response = ls_handler("ls |Q", ctx["parser"])
        assert response.error == ""
        assert response.buffer_output.splitlines() == [
            "Q.Q.q1",
            "CS.Q.cs1",
            "MONITOR.Q.monitor1",
        ]

        assert ctx["parser"].parse("new |QCS /qcs") is None
        modules = layout_registry.get_bound_layout_modules(ctx, "|QCS")
        assert modules == ["|MONITOR.QCS.monitor1", "|CS.QCS.cs1"]

        cs_instance = layout_registry.get_instance(ctx, "|CS.QCS.cs1")
        monitor_instance = layout_registry.get_instance(ctx, "|MONITOR.QCS.monitor1")
        assert cs_instance.config.get("alias_target") == "|Q"
        assert monitor_instance.config.get("alias_target") == "|Q"
        assert monitor_instance.config.get("target") == "|Q:buffer"

        layout_registry.set_active_handle(ctx, "|QCS")
        lines, prompt = layout_registry.build_screen(ctx)
        joined = "\n".join(lines)
        assert "[QCS]" in joined or "[CS[QCS]]" in joined
        assert "cs>" not in joined
        assert prompt == "cs> "
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_cs_row_does_not_echo_layout_buffer_tail(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        ctx["parser"].parse("echo foo!")
        lines, prompt = layout_registry.build_screen(ctx)
        joined = "\n".join(lines)
        assert joined.count("foo!") == 1
        assert "[CS] -> |MONITOR.CS.monitor1" in joined or "[CS[CS]] -> |MONITOR.CS.monitor1" in joined or "[CS[|CS]] -> |MONITOR.CS.monitor1" in joined
        assert prompt == "cs> "
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_startup_cs_plain_text_does_not_clear_monitor_target(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        monitor = layout_registry.get_instance(ctx, "|MONITOR.CS.monitor1")
        assert monitor.config.get("target") == "|CS:buffer"

        result = layout_registry.dispatch_line(ctx, "plain-text-should-not-break-monitor")
        assert result == {"mode": "none"}
        assert monitor.config.get("target") == "|CS:buffer"
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_cs_plain_text_passes_to_active_q_module(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        result = layout_registry.dispatch_line(ctx, "hello-through-cs")
        assert result == {"mode": "self"}

        _wait_until(lambda: ctx["state"].get("$Q:response").get("result") == "hello-through-cs")
        assert ctx["state"].get("$Q:response") == {"error": "", "result": "hello-through-cs"}
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_q_and_qc_commands_work_end_to_end(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert ctx["parser"].parse("qc $OUT stateless-check") is None
        assert ctx["state"].get("$OUT") == {"error": "", "result": "stateless-check"}

        assert ctx["parser"].parse("q stateful-check") is None
        _wait_until(lambda: ctx["state"].get("$Q:response").get("result") == "stateful-check")
        assert ctx["state"].get("$Q:response") == {"error": "", "result": "stateful-check"}

        history = ctx["state"].get("$Q:ch")
        assert history["error"] == ""
        assert isinstance(history["result"], dict)
        latest = history["result"][sorted(history["result"].keys(), key=int)[-1]]
        assert latest.get("prompt") == "stateful-check"
        assert latest.get("response") == "stateful-check"
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_cp_hash_and_dollar_structural_semantics(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        state = ctx["state"]
        assert state.write_state("$JSON", '{"a": {"b": "c"}}', writer="test", op="seed")["error"] == ""

        assert ctx["parser"].parse("cp $JSON #DST") is None
        assert state.get("#DST:a:b") == {"error": "", "result": "c"}

        assert ctx["parser"].parse("cp #DST $DSTJSON") is None
        out = state.get("$DSTJSON")
        assert out["error"] == ""
        assert json.loads(out["result"]) == {"a": {"b": "c"}}
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_bare_instance_command_switches_active_layout(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert layout_registry.get_active_handle(ctx) == "|Q"

        assert ctx["parser"].parse("|CS") is None
        assert layout_registry.get_active_handle(ctx) == "|CS"

        assert ctx["parser"].parse("|Q") is None
        assert layout_registry.get_active_handle(ctx) == "|Q"
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase24_bind_alt_slot_to_bare_instance_command(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert ctx["parser"].parse("bind alt-1 |CS") is None
        from system.layout.keymap import dispatch_key

        assert dispatch_key(ctx, "alt-1") is True
        assert layout_registry.get_active_handle(ctx) == "|CS"
    finally:
        _close_ctx(ctx)
        server.shutdown()
