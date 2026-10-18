"""The Kiro gateway (jwadow/kiro-gateway, a local Anthropic-style proxy to Amazon's Kiro) as a
talker for evals only. Free and rate-limited, so the runner calls it one at a time.

What it is not: Kiro has no system role, so the gateway pastes our system blocks into the first
user message; Amazon adds a hidden coding-assistant prompt of about 1,000 to 5,000 tokens; and the
gateway drops temperature and tool_choice. Thinking is turned off on every request. Results here are
a cross-model check, never a measurement of the live talker.
"""

from __future__ import annotations

import os
import time

from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.models.anthropic import AnthropicTalker
from companion.models.wire import integer, obj, seq, string

URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000") + "/v1/messages"
PREFIX = "kiro/"


def kiro_key() -> str:
    return os.environ.get("KIRO_GATEWAY_API_KEY") or os.environ.get("PROXY_API_KEY", "")


class KiroTalker(AnthropicTalker):
    def body(self, request: TalkerRequest) -> dict[str, object]:
        body = super().body(request)
        body["thinking"] = {"type": "disabled"}  # the gateway's injected reasoning, off
        return body

    async def reply(self, request: TalkerRequest) -> Reply:
        started = time.perf_counter()
        resp = await self._client.post(
            URL,
            headers={
                "x-api-key": self._key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=self.body(request),
            timeout=120,
        )
        resp.raise_for_status()
        data = obj(resp.json())
        blocks = [obj(b) for b in seq(data.get("content"))]
        text = "".join(string(b.get("text")) for b in blocks if b.get("type") == "text").strip()
        usage = obj(data.get("usage"))
        return Reply(
            text=text,
            model=PREFIX + string(data.get("model"), self._model),
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=integer(usage.get("input_tokens")),
        )
