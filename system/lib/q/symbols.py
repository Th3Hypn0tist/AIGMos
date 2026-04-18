from __future__ import annotations

from system.cs.runtime_ctx import get_layout_caller_handle, get_runtime


def q_sampler_prefix_for_profile(profile_name: str) -> str:
    clean = str(profile_name or "default").strip() or "default"
    if clean == "default":
        return "$Q"
    return f"$Q.{clean}"


def q_state_prefix_for_profile(profile_name: str) -> str:
    clean = str(profile_name or "default").strip() or "default"
    if clean == "default":
        return "$Q"
    return f"$Q.{clean}"


def q_state_prefix_for_handle(handle: str) -> str:
    clean = str(handle or "").strip()
    if not clean.startswith("|"):
        return ""
    body = clean[1:].strip()
    if not body:
        return ""
    if ':' not in clean:
        return ""
    return clean


def q_state_prefix_for_state(state, profile_name: str = "default") -> str:
    runtime = getattr(state, "_aigmos_runtime", None)
    if isinstance(runtime, dict):
        root = str(runtime.get("q_state_root") or "").strip()
        if root:
            return root
        handle = str(runtime.get("layout_caller_handle") or "").strip()
        from_handle = q_state_prefix_for_handle(handle)
        if from_handle:
            return from_handle
    return q_state_prefix_for_profile(profile_name)


def q_state_prefix_for_runtime(parser, profile_name: str = "default") -> str:
    root = str(get_runtime(parser, "q_state_root", "") or "").strip()
    if root:
        return root
    handle = get_layout_caller_handle(parser)
    from_handle = q_state_prefix_for_handle(handle)
    if from_handle:
        return from_handle
    return q_state_prefix_for_profile(profile_name)


def role_symbol_for_profile(profile_name: str) -> str:
    return f"{q_state_prefix_for_profile(profile_name)}:role"


def system_prompt_symbol_for_profile(profile_name: str) -> str:
    return f"{q_state_prefix_for_profile(profile_name)}:system_prompt"


def chat_symbol_for_profile(profile_name: str) -> str:
    return f"{q_state_prefix_for_profile(profile_name)}:ch"


def chat_symbol_for_runtime(parser, profile_name: str = "default") -> str:
    return f"{q_state_prefix_for_runtime(parser, profile_name)}:ch"


def get_active_chat_symbol(parser) -> str:
    value = get_runtime(parser, "q_chat_symbol", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return chat_symbol_for_runtime(parser, "default")


def response_symbol_for_profile(profile_name: str) -> str:
    return f"{q_state_prefix_for_profile(profile_name)}:response"


def response_symbol_for_runtime(parser, profile_name: str = "default") -> str:
    return f"{q_state_prefix_for_runtime(parser, profile_name)}:response"


def get_active_response_symbol(parser) -> str:
    value = get_runtime(parser, "q_response_symbol", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return response_symbol_for_runtime(parser, "default")


def thinking_symbol_for_profile(profile_name: str) -> str:
    return f"{q_state_prefix_for_profile(profile_name)}:thinking_text"


def thinking_symbol_for_runtime(parser, profile_name: str = "default") -> str:
    return f"{q_state_prefix_for_runtime(parser, profile_name)}:thinking_text"


def get_active_thinking_symbol(parser) -> str:
    value = get_runtime(parser, "q_thinking_symbol", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return thinking_symbol_for_runtime(parser, "default")


def role_symbol_for_runtime(parser, profile_name: str = "default") -> str:
    root = q_state_prefix_for_runtime(parser, profile_name)
    if root.startswith('|') and ':' in root:
        return f"{root}:role:name"
    return f"{root}:role"


def system_prompt_symbol_for_runtime(parser, profile_name: str = "default") -> str:
    root = q_state_prefix_for_runtime(parser, profile_name)
    if root.startswith('|') and ':' in root:
        return f"{root}:role:system_prompt"
    return f"{root}:system_prompt"


__all__ = [
    "q_sampler_prefix_for_profile",
    "q_state_prefix_for_profile",
    "q_state_prefix_for_handle",
    "q_state_prefix_for_state",
    "q_state_prefix_for_runtime",
    "role_symbol_for_profile",
    "system_prompt_symbol_for_profile",
    "chat_symbol_for_profile",
    "chat_symbol_for_runtime",
    "get_active_chat_symbol",
    "response_symbol_for_profile",
    "response_symbol_for_runtime",
    "get_active_response_symbol",
    "thinking_symbol_for_profile",
    "thinking_symbol_for_runtime",
    "get_active_thinking_symbol",
    "role_symbol_for_runtime",
    "system_prompt_symbol_for_runtime",
]
