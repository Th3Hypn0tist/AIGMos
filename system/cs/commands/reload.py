from __future__ import annotations

from system.cs.command_def import CommandDef
from system.cs.models import HandlerResponse
from system.cs.runtime_ctx import force_render, get_ctx
from system.lib.library_reload import reload_help, reload_prompts, reload_role, reload_roles, reload_routines

from system.lib.reload_ops import reload_selected

command = 'reload'
help_short = 'reload [help|roles|role <name>|prompts|routines|layout|config|commands|adapters|inputs|all]'
help_full = """reload command

examples:
- reload help
- reload roles
- reload role system/help
- reload prompts
- reload routines
- reload layout
- reload config
- reload commands
- reload adapters
- reload inputs
- reload all
"""


def _reapply_role_runtime(ctx, role_name: str) -> int:
    from system.layout.instances import _runtime, _apply_q_role_config

    count = 0
    runtime = _runtime(ctx)
    wanted = str(role_name or '').strip().replace('\\', '/').strip('/')
    if not wanted:
        return 0
    for instance in runtime.get('instances', {}).values():
        if getattr(instance, 'MODULE', '') != 'q':
            continue
        configured = str(getattr(instance, 'config', {}).get('role') or '').strip().replace('\\', '/').strip('/')
        if configured != wanted:
            continue
        _apply_q_role_config(ctx, instance)
        count += 1
    return count


def _reapply_all_roles(ctx) -> int:
    from system.layout.instances import _runtime, _apply_q_role_config

    count = 0
    runtime = _runtime(ctx)
    for instance in runtime.get('instances', {}).values():
        if getattr(instance, 'MODULE', '') != 'q':
            continue
        if not str(getattr(instance, 'config', {}).get('role') or '').strip():
            continue
        _apply_q_role_config(ctx, instance)
        count += 1
    return count


def handler(line: str, parser):
    parts = [part for part in str(line or '').split() if part]
    if not parts:
        return HandlerResponse(error='usage: reload <target>')
    target = parts[1].lower() if len(parts) >= 2 else 'config'
    ctx = get_ctx(parser)
    state = parser.state

    try:
        if target == 'help':
            written = reload_help(state)
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded help: {len(written)}")
        if target == 'roles':
            written = reload_roles(state)
            applied = _reapply_all_roles(ctx)
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded roles: {len(written)} files, {applied} q runtime(s)")
        if target == 'role':
            if len(parts) < 3:
                return HandlerResponse(error='usage: reload role <role>')
            role_name = parts[2]
            written = reload_role(state, role_name)
            applied = _reapply_role_runtime(ctx, role_name)
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded role {role_name}: {len(written)} file(s), {applied} q runtime(s)")
        if target == 'prompts':
            written = reload_prompts(state)
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded prompts: {len(written)}")
        if target == 'routines':
            written = reload_routines(state)
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded routines: {len(written)}")
        if target == 'all':
            completed = []
            reload_help(state); completed.append('help')
            reload_roles(state); completed.append('roles')
            _reapply_all_roles(ctx)
            reload_prompts(state); completed.append('prompts')
            reload_routines(state); completed.append('routines')
            completed.extend(reload_selected(parser, ['config', 'commands', 'layout', 'adapters', 'inputs']))
            force_render(parser)
            return HandlerResponse(buffer_output=f"[ok] reloaded: {'/'.join(completed)}")

        completed = reload_selected(parser, [target])
        force_render(parser)
        return HandlerResponse(buffer_output=f"[ok] reloaded: {'/'.join(completed)}")
    except Exception as exc:
        return HandlerResponse(error=str(exc or ''))


def register() -> CommandDef:
    return CommandDef(
        command=command,
        handler=handler,
        help_short=help_short,
        help_full=help_full,
    )
