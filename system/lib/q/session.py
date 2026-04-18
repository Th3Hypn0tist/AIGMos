from __future__ import annotations

from typing import Any, Callable
import time

from .common import read_state_value
from .errors import QCallError
from .live import chunk_q_live, done_q_live, fail_q_live, open_q_live
from .profile import get_profile, resolve_profile_name, resolve_think_value, set_active_profile
from .prompt import expand_prompt_symbols
from .providers import decode_qc_output, extract_chat, profile_has_stream, strip_inline_think_markup
from .sampler import ensure_q_sampler_state
from .state import (
    append_response_stream,
    load_chat,
    load_role,
    merge_thinking_stream,
    open_chat_entry,
    write_chat_entry,
    write_text_symbol,
)
from .symbols import q_state_prefix_for_runtime
from .transport import call_profile, stream_profile


_STREAM_FLUSH_INTERVAL_SECONDS = 0.15


def _stream_flush_due(now: float, last_flush_at: float, interval: float = _STREAM_FLUSH_INTERVAL_SECONDS) -> bool:
    try:
        now_value = float(now)
        last_value = float(last_flush_at)
        interval_value = float(interval)
    except Exception:
        return True
    if last_value <= 0.0:
        return True
    return (now_value - last_value) >= max(0.0, interval_value)


def _coerce_toggle(value: Any, default: bool = True) -> bool:
    if value is None:
        return bool(default)
    clean = str(value).strip().lower()
    if not clean:
        return bool(default)
    if clean in {'0', 'false', 'no', 'off'}:
        return False
    if clean in {'1', 'true', 'yes', 'on'}:
        return True
    return bool(default)


def _resolve_show_thinking(state, q_root: str) -> bool:
    clean = str(q_root or '').strip()
    if not clean:
        return True
    raw = read_state_value(state, f'{clean}:role:view_thinking', True)
    return _coerce_toggle(raw, True)


def _resolve_stream_enabled(state, q_root: str, profile: dict) -> bool:
    clean = str(q_root or '').strip()
    if clean:
        raw = read_state_value(state, f'{clean}:role:stream', None)
        if raw not in (None, ''):
            return _coerce_toggle(raw, True)
    return bool(profile_has_stream(profile))


def _symbols_for_root(q_root: str) -> dict[str, str]:
    root = str(q_root or '').strip()
    if not root:
        return {
            'chat_symbol': '',
            'role_symbol': '',
            'system_prompt_symbol': '',
            'response_symbol': '',
            'thinking_symbol': '',
            'status_symbol': '',
        }
    role_inline = root.startswith('|') and ':' in root
    return {
        'chat_symbol': f'{root}:ch',
        'role_symbol': f'{root}:role:name' if role_inline else f'{root}:role',
        'system_prompt_symbol': f'{root}:role:system_prompt' if role_inline else f'{root}:system_prompt',
        'response_symbol': f'{root}:response',
        'thinking_symbol': f'{root}:thinking_text',
        'status_symbol': f'{root}:status',
    }


def _expand_system_prompt_safe(parser, role_source: str, *, caller_handle_override: str | None = None) -> str:
    raw = str(role_source or '')
    if not raw:
        return ''
    try:
        return expand_prompt_symbols(
            parser,
            raw,
            mode='system_recursive',
            strict=True,
            caller_handle_override=caller_handle_override,
        )
    except Exception:
        return expand_prompt_symbols(
            parser,
            raw,
            mode='normal_inline',
            strict=True,
            caller_handle_override=caller_handle_override,
        )


def _error_response_text(current: str, error: str) -> str:
    base = str(current or '').strip()
    message = f'ERROR: {str(error or "").strip()}'
    return f'{base}\n\n{message}' if base else message


def _queue_complete(parser, queue_meta: dict[str, Any] | None, status: str, *, error: str = '') -> dict[str, Any] | None:
    meta = dict(queue_meta or {})
    alias = str(meta.get('alias') or '').strip()
    q_root = str(meta.get('q_root') or '').strip()
    task_id = str(meta.get('task_id') or '').strip()
    if not alias or not task_id:
        return None
    from .qcue import qcue_complete
    return qcue_complete(parser, alias, q_root, task_id, status, error=error)


def prepare_q_session(
    parser,
    command_token: str,
    prompt: str,
    *,
    q_root_override: str | None = None,
    caller_handle_override: str | None = None,
    profile_name_override: str | None = None,
) -> dict:
    profile_name = str(profile_name_override or '').strip() or resolve_profile_name(parser, command_token, 'q')
    profile = get_profile(parser, profile_name)
    ensure_q_sampler_state(parser.state, profile_name)
    if not profile_name_override:
        set_active_profile(parser, profile_name)

    q_state_root = str(q_root_override or q_state_prefix_for_runtime(parser, profile_name) or '').strip()
    symbols = _symbols_for_root(q_state_root)
    chat_symbol = symbols['chat_symbol']
    system_prompt_symbol = symbols['system_prompt_symbol']
    chat = load_chat(parser.state, chat_symbol) if chat_symbol else {}
    role_source = load_role(parser.state, system_prompt_symbol) if system_prompt_symbol else ''
    role = _expand_system_prompt_safe(parser, role_source, caller_handle_override=caller_handle_override) if role_source else ''
    expanded_prompt = expand_prompt_symbols(
        parser,
        prompt,
        mode='normal_inline',
        strict=False,
        caller_handle_override=caller_handle_override,
    )
    think_value = resolve_think_value(profile, parser.state, profile_name)
    show_thinking = _resolve_show_thinking(parser.state, q_state_root)
    stream_enabled = _resolve_stream_enabled(parser.state, q_state_root, profile)

    return {
        'profile_name': profile_name,
        'profile': profile,
        'state': parser.state,
        'q_state_root': q_state_root,
        'chat_symbol': chat_symbol,
        'role_symbol': symbols['role_symbol'],
        'system_prompt_symbol': system_prompt_symbol,
        'response_symbol': symbols['response_symbol'],
        'thinking_symbol': symbols['thinking_symbol'],
        'status_symbol': symbols['status_symbol'],
        'prompt': prompt,
        'expanded_prompt': expanded_prompt,
        'role': role,
        'chat': chat,
        'stream_enabled': 1 if stream_enabled else 0,
        'think_value': think_value,
        'show_thinking': show_thinking,
        'caller_handle_override': caller_handle_override,
    }


def run_nonstream_session(session: dict) -> str:
    payload = call_profile(
        session['profile'],
        session['expanded_prompt'],
        role=session['role'],
        chat=session['chat'],
        state=session.get('state'),
        profile_name=session.get('profile_name', 'default'),
        think_value=session.get('think_value'),
        q_state_root=session.get('q_state_root'),
    )
    return strip_inline_think_markup(extract_chat(payload, session['profile'].get('chat_message_tag')))


def q_chat(
    parser,
    command_token: str,
    prompt: str,
    *,
    q_root_override: str | None = None,
    caller_handle_override: str | None = None,
    profile_name_override: str | None = None,
    preinitialized: bool = False,
    queue_meta: dict[str, Any] | None = None,
    on_chunk: Callable[[str, str, str, str], None] | None = None,
    on_done: Callable[[str, str, str], None] | None = None,
) -> dict:
    session = prepare_q_session(
        parser,
        command_token,
        prompt,
        q_root_override=q_root_override,
        caller_handle_override=caller_handle_override,
        profile_name_override=profile_name_override,
    )
    profile_name = session['profile_name']
    chat_symbol = session['chat_symbol']
    response_symbol = session['response_symbol']
    thinking_symbol = session['thinking_symbol']
    status_symbol = session['status_symbol']
    q_state_root = session['q_state_root']
    show_thinking = bool(session.get('show_thinking', True))

    if not preinitialized:
        if q_state_root:
            write_text_symbol(parser.state, f'{q_state_root}:prompt', prompt, 'prompt_accept')
            write_text_symbol(parser.state, f'{q_state_root}:error', '', 'error_reset')
        write_text_symbol(parser.state, response_symbol, '', 'response_reset')
        write_text_symbol(parser.state, thinking_symbol, '', 'thinking_reset')
        if status_symbol:
            write_text_symbol(parser.state, status_symbol, 'running', 'status_running')

    key = open_chat_entry(parser.state, chat_symbol, prompt)
    open_q_live(
        parser,
        profile=profile_name,
        chat_symbol=chat_symbol,
        response_symbol=response_symbol,
        thinking_symbol=thinking_symbol,
        key=key,
        prompt=prompt,
        response='',
        thinking='',
    )
    if not session['stream_enabled']:
        try:
            final_text = run_nonstream_session(session)
        except Exception as exc:
            error_text = _error_response_text('', str(exc or ''))
            if status_symbol:
                write_text_symbol(parser.state, status_symbol, 'error', 'status_error')
            if q_state_root:
                write_text_symbol(parser.state, f'{q_state_root}:error', str(exc or ''), 'q_error')
            write_chat_entry(parser.state, chat_symbol, key, prompt, error_text, done=1)
            fail_q_live(
                parser,
                str(exc or ''),
                profile=profile_name,
                chat_symbol=chat_symbol,
                response_symbol=response_symbol,
                thinking_symbol=thinking_symbol,
                key=key,
                prompt=prompt,
                response=error_text,
                thinking='',
            )
            _queue_complete(parser, queue_meta, 'error', error=str(exc or ''))
            raise
        write_chat_entry(parser.state, chat_symbol, key, prompt, final_text, done=1)
        write_text_symbol(parser.state, response_symbol, '', 'response_finalize')
        write_text_symbol(parser.state, thinking_symbol, '', 'thinking_finalize')
        if status_symbol:
            write_text_symbol(parser.state, status_symbol, 'done', 'status_done')
        done_q_live(
            parser,
            profile=profile_name,
            chat_symbol=chat_symbol,
            response_symbol=response_symbol,
            thinking_symbol=thinking_symbol,
            key=key,
            prompt=prompt,
            response=final_text,
            thinking='',
        )
        _queue_complete(parser, queue_meta, 'done')
        if callable(on_done):
            on_done(final_text, chat_symbol, key)
        return {
            'profile': profile_name,
            'chat_symbol': chat_symbol,
            'response_symbol': response_symbol,
            'thinking_symbol': thinking_symbol,
            'chat_key': key,
            'message': final_text,
        }

    final_text = ''
    final_thinking = ''
    last_written_response = ''
    last_flush_at = 0.0
    try:
        for event in stream_profile(
            session['profile'],
            session['expanded_prompt'],
            role=session['role'],
            chat=session['chat'],
            state=session.get('state'),
            profile_name=profile_name,
            think_value=session.get('think_value'),
            q_state_root=q_state_root,
        ):
            raw_thinking_chunk = strip_inline_think_markup(event.get('thinking') or '')
            content_chunk = strip_inline_think_markup(event.get('content') or '')
            event_done = 1 if int(event.get('done') or 0) == 1 else 0

            if raw_thinking_chunk:
                final_thinking = merge_thinking_stream(final_thinking, raw_thinking_chunk)
            if content_chunk:
                final_text = append_response_stream(final_text, content_chunk)

            visible_response = strip_inline_think_markup(final_text)
            visible_thinking = final_thinking if show_thinking else ''

            chunk_q_live(
                parser,
                profile=profile_name,
                chat_symbol=chat_symbol,
                response_symbol=response_symbol,
                thinking_symbol=thinking_symbol,
                key=key,
                prompt=prompt,
                response=visible_response,
                thinking=visible_thinking,
            )

            now = time.monotonic()
            flush_now = event_done or _stream_flush_due(now, last_flush_at)
            if flush_now:
                write_text_symbol(parser.state, response_symbol, visible_response, 'response_partial')
                write_text_symbol(parser.state, thinking_symbol, visible_thinking, 'thinking_partial')
                if visible_response != last_written_response:
                    write_chat_entry(parser.state, chat_symbol, key, prompt, visible_response, done=0)
                    last_written_response = visible_response
                last_flush_at = now

            if callable(on_chunk) and (raw_thinking_chunk or content_chunk):
                on_chunk(content_chunk or raw_thinking_chunk, visible_response, chat_symbol, key)
            if event_done:
                break

        final_text = strip_inline_think_markup(final_text)
        write_chat_entry(parser.state, chat_symbol, key, prompt, final_text, done=1)
        write_text_symbol(parser.state, response_symbol, '', 'response_finalize')
        write_text_symbol(parser.state, thinking_symbol, '', 'thinking_finalize')
        if status_symbol:
            write_text_symbol(parser.state, status_symbol, 'done', 'status_done')
        done_q_live(
            parser,
            profile=profile_name,
            chat_symbol=chat_symbol,
            response_symbol=response_symbol,
            thinking_symbol=thinking_symbol,
            key=key,
            prompt=prompt,
            response=final_text,
            thinking='',
        )
        _queue_complete(parser, queue_meta, 'done')
        if callable(on_done):
            on_done(final_text, chat_symbol, key)
    except Exception as exc:
        error_text = _error_response_text(final_text, str(exc or ''))
        if q_state_root:
            write_text_symbol(parser.state, f'{q_state_root}:error', str(exc or ''), 'q_error')
        if status_symbol:
            write_text_symbol(parser.state, status_symbol, 'error', 'status_error')
        write_chat_entry(parser.state, chat_symbol, key, prompt, error_text, done=1)
        fail_q_live(
            parser,
            str(exc or ''),
            profile=profile_name,
            chat_symbol=chat_symbol,
            response_symbol=response_symbol,
            thinking_symbol=thinking_symbol,
            key=key,
            prompt=prompt,
            response=error_text,
            thinking=final_thinking if show_thinking else '',
        )
        _queue_complete(parser, queue_meta, 'error', error=str(exc or ''))
        raise

    return {
        'profile': profile_name,
        'chat_symbol': chat_symbol,
        'response_symbol': response_symbol,
        'thinking_symbol': thinking_symbol,
        'chat_key': key,
        'message': final_text,
    }


def qc_raw(
    parser,
    command_token: str,
    *args: Any,
    q_root_override: str | None = None,
    caller_handle_override: str | None = None,
    profile_name_override: str | None = None,
) -> dict:
    flat_args: list[Any] = []
    for item in args:
        if isinstance(item, (list, tuple)):
            flat_args.extend(item)
        else:
            flat_args.append(item)
    prompt = ' '.join(str(x) for x in flat_args).strip()
    if not prompt:
        raise QCallError('qc requires prompt')

    profile_name = str(profile_name_override or '').strip() or resolve_profile_name(parser, command_token, 'qc')
    profile = get_profile(parser, profile_name)
    ensure_q_sampler_state(parser.state, profile_name)
    if not profile_name_override:
        set_active_profile(parser, profile_name)

    expanded_prompt = expand_prompt_symbols(
        parser,
        prompt,
        mode='normal_inline',
        strict=False,
        caller_handle_override=caller_handle_override,
    )
    payload = call_profile(
        profile,
        expanded_prompt,
        role='',
        chat={},
        state=parser.state,
        profile_name=profile_name,
        think_value=resolve_think_value(profile, parser.state, profile_name),
        q_state_root=q_root_override or q_state_prefix_for_runtime(parser, profile_name),
    )
    message = strip_inline_think_markup(extract_chat(payload, profile.get('chat_message_tag')))
    decoded = decode_qc_output(payload, profile.get('chat_message_tag'))
    return {'profile': profile_name, 'message': message, 'decoded': decoded}


qc_call = qc_raw

__all__ = ['prepare_q_session', 'run_nonstream_session', 'q_chat', 'qc_raw', 'qc_call']
