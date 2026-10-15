"""Anthropic Messages adapter for the talker. Thinking is never sent, so it stays off."""

from __future__ import annotations

import json
import time

import httpx

from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.models.wire import integer, messages_with_breakpoint, obj, seq, string

URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-4-5"


class AnthropicTalker:
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 400,
    ) -> None:
        self._key = api_key
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def body(self, request: TalkerRequest) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": [
                {
                    "type": "text",
                    "text": request.prefix.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": messages_with_breakpoint(request),
        }
        tools = seq(json.loads(request.prefix.tools_json))
        if tools:
            body["tools"] = tools
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
            timeout=60,
        )
        resp.raise_for_status()
        data = obj(resp.json())
        blocks = [obj(b) for b in seq(data.get("content"))]
        text = "".join(string(b.get("text")) for b in blocks if b.get("type") == "text").strip()
        usage = obj(data.get("usage"))
        return Reply(
            text=text,
            model=string(data.get("model"), self._model),
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=integer(usage.get("input_tokens")),
            cache_read_tokens=integer(usage.get("cache_read_input_tokens")),
            cache_write_tokens=integer(usage.get("cache_creation_input_tokens")),
        )
