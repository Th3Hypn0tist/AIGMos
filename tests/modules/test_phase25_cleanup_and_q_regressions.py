from __future__ import annotations

import ast
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from system.adapters.registry import build_state_request
from system.adapters.sqlite import SQLiteAdapter
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

        data = json.dumps(
            {
                "message": {"content": message},
                "response": message,
                "done": True,
            }
        ).encode("utf-8")

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
    db_path = tmp_path / "phase25_state.db"
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


def test_phase25_command_modules_export_single_register_definition():
    command_dir = Path(__file__).resolve().parents[2] / "system" / "cs" / "commands"
    failures: list[str] = []

    for path in sorted(command_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        register_defs = [
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "register"
        ]
        if len(register_defs) != 1:
            failures.append(f"{path.name}: expected 1 register(), found {len(register_defs)}")

    assert failures == []


def test_phase25_bare_layout_instance_token_switches_active_layout(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert layout_registry.get_active_handle(ctx) == "|Q"

        assert ctx["parser"].parse("|CS") is None
        assert layout_registry.get_active_handle(ctx) == "|CS"
    finally:
        _close_ctx(ctx)
        server.shutdown()


def test_phase25_q_layout_plain_text_updates_history_and_render(tmp_path: Path):
    server, port = _start_echo_server()
    ctx = _build_ctx(tmp_path, port=port)
    try:
        assert ctx["parser"].parse("/q") is None
        assert layout_registry.get_active_handle(ctx) == "|Q"

        result = layout_registry.dispatch_line(ctx, "hello from q layout")
        assert result == {"mode": "self"}

        def _history_ready() -> bool:
            value = layout_state.get_value(ctx, "$Q:ch", {})
            if not isinstance(value, dict) or not value:
                return False
            first = value.get("1") or value.get(1) or {}
            return first.get("response") == "hello from q layout"

        _wait_until(_history_ready)

        history = layout_state.get_value(ctx, "$Q:ch", {})
        first = history.get("1") or history.get(1)
        assert first == {
            "prompt": "hello from q layout",
            "response": "hello from q layout",
            "done": 1,
        }

        lines, prompt = layout_registry.build_screen(ctx)
        joined = "\n".join(lines)
        assert "q> hello from q layout" in joined
        assert "a> hello from q layout" in joined
        assert prompt == "cs> "
    finally:
        _close_ctx(ctx)
        server.shutdown()
