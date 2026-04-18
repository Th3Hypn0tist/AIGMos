from __future__ import annotations

from typing import Optional

from system.cs.symbols import parse_assignment, parse_runner_control
from system.runtime.runner import runner_control, set_runner_autostart
from system.runtime.runner_store import set_runner_autostart as set_runner_autostart_persistent
from system.runtime.runner_store import set_runner_mode_persistent
from system.state.api import write_value

from system.cs.reporter import handle_error
from system.cs.resolver import maybe_expand_direct_exec_symbol, resolve_assignment_rhs
from system.lib.trigger.lifecycle import set_trigger_pulse, validate_event_write, validate_trigger_write


def parse_symbol_line(parser, line: str) -> Optional[str]:
    try:
        runner_cmd = parse_runner_control(line)
        if runner_cmd is not None:
            runner_control(runner_cmd["target"], runner_cmd["token"])

            if runner_cmd["token"] in {"once", "cycle", "loop"}:
                set_runner_mode_persistent(
                    parser.state,
                    runner_cmd["target"],
                    runner_cmd["token"],
                )

            return None

        if "=" in line:
            assign = parse_assignment(line)

            if assign["target"].startswith("%") and assign["target"].endswith(".autostart"):
                runner_name = assign["target"].rsplit(".", 1)[0]
                autostart = set_runner_autostart_persistent(
                    parser.state,
                    runner_name,
                    assign["value"],
                )
                set_runner_autostart(runner_name, autostart)
                return None

            resolved_value = resolve_assignment_rhs(parser, assign["value"])
            target = str(assign["target"] or '').strip()

            if target.startswith('!'):
                try:
                    validated = validate_trigger_write(target, resolved_value)
                    set_trigger_pulse(parser, validated['name'], validated['normalized_value'])
                except Exception as exc:
                    return handle_error(parser, line, str(exc))
                return None

            if target.startswith('@'):
                try:
                    validate_event_write(target, resolved_value)
                except Exception as exc:
                    return handle_error(parser, line, str(exc))
                return None

            result = write_value(
                parser.state,
                target,
                resolved_value,
                writer="parser:assignment",
                op="assignment",
            )
            if result["error"]:
                return handle_error(parser, line, result["error"])

            return None

        expanded = maybe_expand_direct_exec_symbol(parser, line)
        if expanded != line:
            return parser.parse(expanded)

        return handle_error(parser, line, f"unsupported symbol syntax: {line}")

    except Exception as exc:
        return handle_error(parser, line, f"symbol handler crash: {exc}")
