from __future__ import annotations

from typing import Any
import re

from system.layout import state as layout_state
from system.layout.lib.editor import get_module_ui
from system.lib.q.qcue import qcue_lookup_root
from system.layout.lib.scroll import viewport_head, viewport_tail
from system.layout.lib.wrap import wrap_text

_THINK_TAG_RE = re.compile(r"</?think>", re.IGNORECASE)
_PROMPT_DIVIDER = "***************PROMPT***************"


def _clean_visible(value: Any) -> str:
    return _THINK_TAG_RE.sub('', str(value or ''))


def sorted_chat_keys(chat: dict[str, Any]) -> list[Any]:
    def sort_key(item: Any):
        text = str(item)
        return (0, int(text)) if text.isdigit() else (1, text)
    return sorted(chat.keys(), key=sort_key)


def _live_packet_for(ctx, chat_symbol: str) -> tuple[dict[str, Any], Any]:
    parser = ctx.get('parser') if isinstance(ctx, dict) else None
    live_packet: dict[str, Any] = {}
    chat: Any = layout_state.get_value(ctx, chat_symbol, {})
    if parser is None:
        return live_packet, chat
    try:
        from system.lib.q.live import get_live_chat, get_live_packet
        chat = get_live_chat(parser, chat_symbol)
        live_packet = get_live_packet(parser, chat_symbol)
    except Exception:
        pass
    return live_packet, chat


def _cue_text_from_info(queue_info: dict[str, Any] | None) -> str:
    if not isinstance(queue_info, dict):
        return ''
    status = str(queue_info.get('status') or '').strip().lower()
    if status != 'waiting':
        return ''
    position = queue_info.get('position')
    total = queue_info.get('queue_total')
    if position is not None and total is not None:
        return f'[CUE {position}/{total}]'
    return '[WAITING]'


def read_q_state(ctx, instance) -> dict[str, Any]:
    target_root = str(getattr(instance, 'primary_target', '') or '').strip()
    chat_symbol = str(getattr(instance, 'view_target', '') or '').strip()
    show_thinking_raw = layout_state.get_value(ctx, f'{target_root}:role:view_thinking', True)
    show_thinking = str(True if show_thinking_raw is None else show_thinking_raw).strip().lower() not in {'0', 'false', 'no', 'off'}
    live_packet, chat = _live_packet_for(ctx, chat_symbol)
    local_prompt = _clean_visible(layout_state.get_value(ctx, f'{target_root}:prompt', '') or '')
    local_response = _clean_visible(layout_state.get_value(ctx, f'{target_root}:response', '') or '')
    local_thinking = _clean_visible(layout_state.get_value(ctx, f'{target_root}:thinking_text', '') or '')
    local_error = _clean_visible(layout_state.get_value(ctx, f'{target_root}:error', '') or '')
    local_status = str(layout_state.get_value(ctx, f'{target_root}:status', '') or '').strip().lower()
    prefer_alias = str(layout_state.get_value(ctx, f'{target_root}:queue_alias', '') or '').strip()
    queue_info = qcue_lookup_root(ctx.get('state'), target_root, prefer_alias=prefer_alias) if target_root else None
    queue_status = str((queue_info or {}).get('status') or '').strip().lower()
    status = queue_status or local_status
    display_prompt = local_prompt or _clean_visible((queue_info or {}).get('prompt') or '')
    return {
        'target_root': target_root,
        'chat_symbol': chat_symbol,
        'chat': chat,
        'prompt': display_prompt,
        'response': local_response,
        'thinking': local_thinking,
        'error': local_error,
        'status': status,
        'queue_status': queue_status,
        'queue_info': queue_info or {},
        'cue_text': _cue_text_from_info(queue_info),
        'live_packet': live_packet,
        'show_thinking': show_thinking,
    }


def _extend_wrapped(dst: list[str], raw: str, width: int) -> None:
    dst.extend(wrap_text(raw, width) or [''])


def _entry_block(prompt: str, response: str, error: str, width: int) -> list[str]:
    lines: list[str] = []
    if prompt:
        _extend_wrapped(lines, _PROMPT_DIVIDER, width)
        _extend_wrapped(lines, f'Q> {prompt}', width)
    if response:
        _extend_wrapped(lines, f'A> {response}', width)
    if error:
        _extend_wrapped(lines, f'[ERROR] {error}', width)
    if lines:
        lines.append('')
    return lines


def _live_block(prompt: str, response: str, thinking: str, status: str, show_thinking: bool, width: int) -> list[str]:
    lines: list[str] = []
    if prompt:
        _extend_wrapped(lines, _PROMPT_DIVIDER, width)
        _extend_wrapped(lines, f'Q> {prompt}', width)
    if response:
        _extend_wrapped(lines, f'[RESPONSE] {response}', width)
    elif thinking and show_thinking:
        _extend_wrapped(lines, f'[THINKING] {thinking}', width)
    elif status == 'running':
        _extend_wrapped(lines, '[Thinking...]', width)
    return lines


def _waiting_block(prompt: str, cue_text: str, width: int) -> list[str]:
    lines: list[str] = []
    if prompt:
        _extend_wrapped(lines, _PROMPT_DIVIDER, width)
        _extend_wrapped(lines, f'Q> {prompt}', width)
    _extend_wrapped(lines, cue_text or '[WAITING]', width)
    return lines


def render_q_lines(ctx, instance, width: int, height: int, flow: str = 'top') -> list[str]:
    width = max(1, int(width or 1))
    height = max(1, int(height or 1))
    flow = str(flow or 'top').strip().lower()
    ui = get_module_ui(ctx, getattr(instance, 'handle', ''))
    follow = bool(ui.get('follow', True))
    scroll = max(0, int(ui.get('scroll', 0) or 0))

    state = read_q_state(ctx, instance)
    live_packet = state['live_packet']
    live_chat_symbol = str(live_packet.get('chat_symbol') or '')
    live_key = str(live_packet.get('key') or '')
    live_prompt = _clean_visible(live_packet.get('prompt') or state['prompt'] or '')
    live_response = _clean_visible(live_packet.get('response') or '')
    live_thinking = _clean_visible(live_packet.get('thinking') or '')
    live_done = 1 if int(live_packet.get('done') or 0) == 1 else 0

    is_live_for_target = (
        live_done == 0
        and live_chat_symbol == state['chat_symbol']
        and bool(live_key)
    ) or state['status'] == 'running'

    blocks: list[list[str]] = []
    if state['error']:
        blocks.append(wrap_text(f'[ERROR] {state["error"]}', width) or [''])

    if state['status'] == 'waiting':
        blocks.append(_waiting_block(state['prompt'], state['cue_text'], width))
    elif is_live_for_target:
        blocks.append(_live_block(live_prompt or state['prompt'], live_response or state['response'], live_thinking or state['thinking'], state['status'], state['show_thinking'], width))
    else:
        chat = state['chat']
        if isinstance(chat, dict) and chat:
            for key in sorted_chat_keys(chat):
                item = chat.get(key) or {}
                if not isinstance(item, dict):
                    continue
                block = _entry_block(
                    _clean_visible(item.get('prompt') or ''),
                    _clean_visible(item.get('response') or ''),
                    _clean_visible(item.get('error') or ''),
                    width,
                )
                if block:
                    blocks.append(block)
        elif state['prompt'] or state['response'] or state['thinking'] or state['error']:
            blocks.append(_entry_block(state['prompt'], state['response'] or state['thinking'], state['error'], width))

    all_lines: list[str] = []
    for block in blocks:
        all_lines.extend(block)

    if not all_lines:
        all_lines = ['']

    if follow:
        ui['scroll'] = 0
        if flow == 'top':
            return viewport_head(all_lines, height, 0)
        return viewport_tail(all_lines, height, 0)
    if flow == 'top':
        return viewport_head(all_lines, height, scroll)
    return viewport_tail(all_lines, height, scroll)


def clear_q_state(ctx, module_handle: str, instance, *, clear_data: bool) -> bool:
    if clear_data:
        base = str(getattr(instance, 'primary_target', '') or '').strip()
        if base:
            layout_state.set_value(ctx, f'{base}:ch', {})
            layout_state.set_value(ctx, f'{base}:response', '')
            layout_state.set_value(ctx, f'{base}:thinking_text', '')
            layout_state.set_value(ctx, f'{base}:prompt', '')
            layout_state.set_value(ctx, f'{base}:error', '')
            layout_state.set_value(ctx, f'{base}:status', '')
    ui = get_module_ui(ctx, module_handle)
    ui['follow'] = True
    ui['scroll'] = 0
    return True


__all__ = [
    'sorted_chat_keys',
    'read_q_state',
    'render_q_lines',
    'clear_q_state',
]
