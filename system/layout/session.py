from __future__ import annotations

from typing import Any, Callable

from .errors import QCallError
from .live import chunk_q_live, done_q_live, fail_q_live, open_q_live
from .profile import get_profile, resolve_profile_name, resolve_think_value, set_active_profile
from .prompt import expand_prompt_symbols
from .providers import decode_qc_output, profile_has_stream, extract_chat, strip_inline_think_markup
from .sampler import ensure_q_sampler_state
from .state import merge_thinking_stream, append_response_stream, write_text_symbol, load_chat, load_role, open_chat_entry, save_chat, write_chat_entry
from .symbols import (
    chat_symbol_for_runtime,
    q_state_prefix_for_runtime,
    response_symbol_for_runtime,
    role_symbol_for_runtime,
    system_prompt_symbol_for_runtime,
    thinking_symbol_for_runtime,
)
from .transport import call_profile, stream_profile
from .common import read_state_value


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
        coerced = _coerce_toggle(raw, default=True) if raw not in (None, '') else None
        if coerced is not None:
            return bool(coerced)
    return bool(profile_has_stream(profile))


def prepare_q_session(parser, command_token: str, prompt: str) -> dict:
    profile_name = resolve_profile_name(parser, command_token, 'q')
    profile = get_profile(parser, profile_name)
    ensure_q_sampler_state(parser.state, profile_name)
    set_active_profile(parser, profile_name)

    q_state_root = q_state_prefix_for_runtime(parser, profile_name)
    chat_symbol = chat_symbol_for_runtime(parser, profile_name)
    role_symbol = role_symbol_for_runtime(parser, profile_name)
    system_prompt_symbol = system_prompt_symbol_for_runtime(parser, profile_name)
    chat = load_chat(parser.state, chat_symbol)
    role_source = load_role(parser.state, system_prompt_symbol)
    role = expand_prompt_symbols(parser, role_source, mode='system_recursive', strict=True) if role_source else ''
    expanded_prompt = expand_prompt_symbols(parser, prompt, mode='normal_inline', strict=False, max_passes=16)
    think_value = resolve_think_value(profile, parser.state, profile_name)
    show_thinking = _resolve_show_thinking(parser.state, q_state_root)
    stream_enabled = _resolve_stream_enabled(parser.state, q_state_root, profile)

    return {
        'profile_name': profile_name,
        'profile': profile,
        'state': parser.state,
        'q_state_root': q_state_root,
        'chat_symbol': chat_symbol,
        'role_symbol': role_symbol,
        'system_prompt_symbol': system_prompt_symbol,
        'prompt': prompt,
        'expanded_prompt': expanded_prompt,
        'role': role,
        'chat': chat,
        'stream_enabled': 1 if stream_enabled else 0,
        'think_value': think_value,
        'show_thinking': show_thinking,
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


def q_chat(parser, command_token: str, prompt: str, on_chunk: Callable[[str, str, str, str], None] | None = None, on_done: Callable[[str, str, str], None] | None = None) -> dict:
    session = prepare_q_session(parser, command_token, prompt)
    profile_name = session['profile_name']
    chat_symbol = session['chat_symbol']
    response_symbol = response_symbol_for_runtime(parser, profile_name)
    thinking_symbol = thinking_symbol_for_runtime(parser, profile_name)
    show_thinking = bool(session.get('show_thinking', True))

    write_text_symbol(parser.state, response_symbol, '', 'response_reset')
    write_text_symbol(parser.state, thinking_symbol, '', 'thinking_reset')

    open_q_live(parser, profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key='', prompt=prompt, response='', thinking='')

    if not session['stream_enabled']:
        final_text = run_nonstream_session(session)
        chat_log = dict(session['chat'])
        key = str(max([int(k) for k in chat_log.keys() if str(k).isdigit()] + [0]) + 1)
        chat_log[key] = {'prompt': prompt, 'response': final_text, 'done': 1}
        save_chat(parser.state, chat_symbol, chat_log)
        write_text_symbol(parser.state, response_symbol, '', 'response_finalize')
        write_text_symbol(parser.state, thinking_symbol, '', 'thinking_finalize')
        done_q_live(parser, profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key=key, prompt=prompt, response=final_text, thinking='')
        if callable(on_done):
            on_done(final_text, chat_symbol, key)
        return {'profile': profile_name, 'chat_symbol': chat_symbol, 'response_symbol': response_symbol, 'thinking_symbol': thinking_symbol, 'chat_key': key, 'message': final_text}

    key = open_chat_entry(parser.state, chat_symbol, prompt)
    final_text = ''
    final_thinking = ''
    last_written_response = ''

    open_q_live(parser, profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key=key, prompt=prompt, response='', thinking='')

    try:
        for event in stream_profile(
            session['profile'],
            session['expanded_prompt'],
            role=session['role'],
            chat=session['chat'],
            state=session.get('state'),
            profile_name=session.get('profile_name', 'default'),
            think_value=session.get('think_value'),
            q_state_root=session.get('q_state_root'),
        ):
            raw_thinking_chunk = strip_inline_think_markup(event.get('thinking') or '')
            content_chunk = strip_inline_think_markup(event.get('content') or '')
            event_done = 1 if int(event.get('done') or 0) == 1 else 0

            thinking_chunk = raw_thinking_chunk

            if thinking_chunk:
                final_thinking = merge_thinking_stream(final_thinking, thinking_chunk)
            if content_chunk:
                final_text = append_response_stream(final_text, content_chunk)

            visible_response = strip_inline_think_markup(final_text)
            visible_thinking = final_thinking if show_thinking else ''

            write_text_symbol(parser.state, response_symbol, visible_response, 'response_partial')
            write_text_symbol(parser.state, thinking_symbol, visible_thinking, 'thinking_partial')
            if visible_response != last_written_response:
                write_chat_entry(parser.state, chat_symbol, key, prompt, visible_response, done=0)
                last_written_response = visible_response
            chunk_q_live(parser, profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key=key, prompt=prompt, response=visible_response, thinking=visible_thinking)

            if callable(on_chunk) and (thinking_chunk or content_chunk):
                on_chunk(content_chunk or thinking_chunk, visible_response, chat_symbol, key)

            if event_done == 1:
                break

        final_text = strip_inline_think_markup(final_text)
        write_chat_entry(parser.state, chat_symbol, key, prompt, final_text, done=1)
        write_text_symbol(parser.state, response_symbol, '', 'response_finalize')
        write_text_symbol(parser.state, thinking_symbol, '', 'thinking_finalize')
        done_q_live(parser, profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key=key, prompt=prompt, response=final_text, thinking='')

        if callable(on_done):
            on_done(final_text, chat_symbol, key)

    except Exception:
        final_text = strip_inline_think_markup(final_text)
        visible_thinking = final_thinking if show_thinking else ''
        write_chat_entry(parser.state, chat_symbol, key, prompt, final_text, done=0)
        write_text_symbol(parser.state, response_symbol, final_text, 'response_partial')
        write_text_symbol(parser.state, thinking_symbol, visible_thinking, 'thinking_partial')
        fail_q_live(parser, 'q stream interrupted', profile=profile_name, chat_symbol=chat_symbol, response_symbol=response_symbol, thinking_symbol=thinking_symbol, key=key, prompt=prompt, response=final_text, thinking=visible_thinking)
        raise

    return {'profile': profile_name, 'chat_symbol': chat_symbol, 'response_symbol': response_symbol, 'thinking_symbol': thinking_symbol, 'chat_key': key, 'message': final_text}


def qc_raw(parser, command_token: str, *args: Any) -> dict:
    flat_args: list[Any] = []
    for item in args:
        if isinstance(item, (list, tuple)):
            flat_args.extend(item)
        else:
            flat_args.append(item)
    if not flat_args:
        raise QCallError('qc requires prompt')
    prompt = ' '.join(str(x) for x in flat_args).strip()
    if not prompt:
        raise QCallError('qc requires prompt')

    profile_name = resolve_profile_name(parser, command_token, 'qc')
    profile = get_profile(parser, profile_name)
    ensure_q_sampler_state(parser.state, profile_name)
    set_active_profile(parser, profile_name)

    payload = call_profile(
        profile,
        expand_prompt_symbols(parser, prompt, mode='normal_inline', strict=False, max_passes=16),
        role='',
        chat={},
        state=parser.state,
        profile_name=profile_name,
        q_state_root=q_state_prefix_for_runtime(parser, profile_name),
    )
    output = decode_qc_output(payload, profile.get('chat_message_tag'))
    return {'profile': profile_name, 'output': output}


__all__ = ['prepare_q_session', 'run_nonstream_session', 'q_chat', 'qc_raw']
