# q payload structure

{
  "model": "<alias provided>",
  "messages": [
    { "role": "system", "content": (|<instance>:<q id>:role:system_prompt) },
    { "role": "user", "content": "<chat history> <prompt>" }
  ],
  "stream": (|<instance>:<q id>:role:stream),
  "think": (|<instance>:<q id>:role:think),
  "options": {
    "temperature": (|<instance>:<q id>:role:temperature),
    "top_k": (|<instance>:<q id>:role:top_k),
    "top_p": (|<instance>:<q id>:role:top_p),
    "repeat_penalty": (|<instance>:<q id>:role:repeat_penalty)
  }
}

Rules:
- `system_prompt` source is `|<instance>:<q id>:role:system_prompt`
- if `system_prompt` is empty or null, omit the system message entirely
- `q` includes chat history, because `q` is chatbot mode
- chat history + current prompt are packed into the single user message content
- `stream` and `think` are top-level payload fields
- samplers exist only under `options`
- do not duplicate sampler fields at top level
- do not include `stop` in outbound payload
- do not include any separate role payload block
- typo fixed: `history`, not `hisotry`
