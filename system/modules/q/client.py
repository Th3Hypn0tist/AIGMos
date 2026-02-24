# modules/q/client.py
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


@dataclass(frozen=True)
class QConfig:
    base_url: str
    timeout_ms: int = 8000
    poll_interval_ms: int = 200
    model: str = "llama3.1:8b"


class QChatError(RuntimeError):
    pass


class QChatTimeout(QChatError):
    pass


class QChat:
    """
    Minimal chat-only Q client.
    Returns ONLY assistant text (result.text) on success.

    Usage:
        q = QChat("../config/llm/default.json")
        text = await q.chat(messages)
    """

    def __init__(self, config_path: str | Path):
        self._cfg_path = Path(config_path)
        self.cfg = self._load_config(self._cfg_path)

    @staticmethod
    def _load_config(path: Path) -> QConfig:
        if not path.exists():
            raise FileNotFoundError(f"Q config not found: {path}")

        raw = json.loads(path.read_text(encoding="utf-8"))

        base_url = (raw.get("base_url") or "").strip()
        if not base_url:
            raise ValueError("config.base_url missing/empty")

        timeout_ms = int(raw.get("timeout_ms", 8000))
        poll_interval_ms = int(raw.get("poll_interval_ms", 200))
        model = (raw.get("model") or "llama3.1:8b").strip()

        if timeout_ms < 0:
            timeout_ms = 0
        if poll_interval_ms < 0:
            poll_interval_ms = 0

        return QConfig(
            base_url=base_url.rstrip("/"),
            timeout_ms=timeout_ms,
            poll_interval_ms=poll_interval_ms,
            model=model,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        timeout_ms: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> str:
        """
        messages: [{role, content}, ...]
        returns: result.text (string) ONLY
        """
        cfg = self.cfg
        overall_timeout_ms = cfg.timeout_ms if timeout_ms is None else int(timeout_ms)
        poll_ms = cfg.poll_interval_ms

        # Basic validation (minimal, but prevents silent weirdness)
        if not isinstance(messages, list):
            raise TypeError("messages must be a list")
        for m in messages:
            if not isinstance(m, dict) or "role" not in m or "content" not in m:
                raise ValueError("each message must be dict with keys: role, content")

        # Build standard payload. No simulate knobs.
        args: Dict[str, Any] = {"messages": messages}
        # Keep contract realistic: include model
        if cfg.model:
            args["model"] = cfg.model

        payload: Dict[str, Any] = {
            "op": "llm.chat",
            "args": args,
            "timeout_ms": overall_timeout_ms,
        }
        if trace_id:
            payload["trace_id"] = trace_id

        t0 = time.monotonic()
        deadline = t0 + (overall_timeout_ms / 1000.0 if overall_timeout_ms > 0 else 0.0)

        async with httpx.AsyncClient(base_url=cfg.base_url) as client:
            job_id = await self._submit(client, payload)

            try:
                while True:
                    status = await self._get_status(client, job_id)
                    state = status.get("state")

                    if state == "ok":
                        result = status.get("result") or {}
                        text = result.get("text")
                        if not isinstance(text, str):
                            raise QChatError("Malformed response: result.text missing")
                        return text

                    if state in ("fail", "timeout", "cancelled"):
                        err = status.get("error") or {}
                        code = err.get("code", "ERROR")
                        msg = err.get("message", "unknown error")
                        raise QChatError(f"{code}: {msg}")

                    # queued / running / unknown -> keep polling
                    if overall_timeout_ms > 0 and time.monotonic() >= deadline:
                        # best-effort cancel
                        await self._cancel_silent(client, job_id)
                        raise QChatTimeout("Q timeout")

                    if poll_ms > 0:
                        await asyncio.sleep(poll_ms / 1000.0)
                    else:
                        await asyncio.sleep(0)

            except Exception:
                # If something blows up mid-flight, best-effort cancel to avoid hangs.
                await self._cancel_silent(client, job_id)
                raise

    async def _submit(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> str:
        try:
            r = await client.post("/v1/jobs", json=payload, timeout=10.0)
        except Exception as e:
            raise QChatError(f"submit failed: {e}") from e

        if r.status_code not in (200, 201):
            raise QChatError(f"submit failed: HTTP {r.status_code} :: {r.text}")

        data = r.json()
        job_id = data.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise QChatError("submit failed: missing job id")
        return job_id

    async def _get_status(self, client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
        try:
            r = await client.get(f"/v1/jobs/{job_id}", timeout=10.0)
        except Exception as e:
            raise QChatError(f"poll failed: {e}") from e

        if r.status_code != 200:
            raise QChatError(f"poll failed: HTTP {r.status_code} :: {r.text}")

        data = r.json()
        if not isinstance(data, dict):
            raise QChatError("poll failed: non-object json")
        return data

    async def _cancel_silent(self, client: httpx.AsyncClient, job_id: str) -> None:
        try:
            await client.post(f"/v1/jobs/{job_id}/cancel", timeout=5.0)
        except Exception:
            return
