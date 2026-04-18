from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.lib.trigger.api import define_trigger_from_command

command = "trig"
help_short = 'trig !name <expr> | trig !name onchange <ref> | trig !name cron "spec"'
help_full = """create ! trigger

forms:
  trig !name <expr>
  trig !name onchange <ref>
  trig !name cron "spec"

expr operators:
  == != < <= > >= AND OR XOR NOT

rules:
  - logical expressions using AND / OR / XOR / NOT must be grouped with parentheses
  - first seen onchange value seeds baseline and does not fire
  - writable control field: !name:pulse = <ms>
  - readable runtime field: !name:state

examples:
  trig !sensor.hot $UM.sensor:temp >= 40
  trig !sensor.change onchange $UM.sensor:temp
  trig !heartbeat cron "every 1s"
  trig !backup cron "daily"
  !sensor.hot:pulse = 100
"""

def handler(line: str, parser) -> HandlerResponse:
    try:
        define_trigger_from_command(parser, line)
    except ValueError as exc:
        return HandlerResponse(error=str(exc))
    return HandlerResponse(buffer_output='[ok]')



def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
