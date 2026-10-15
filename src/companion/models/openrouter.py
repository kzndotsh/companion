"""OpenRouter adapter for the talker. Provider is pinned, fallbacks off, reasoning off."""

from __future__ import annotations

import time

import httpx

from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.models.wire import integer, obj, seq, string

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_PROVIDER = "Anthropic"


class OpenRouterTalker:
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient,
        model: str = DEFAULT_MODEL,
        provider: str = DEFAULT_PROVIDER,
        max_tokens: int = 400,
    ) -> None:
        self._key = api_key
        self._client = client
        self._model = model
        self._provider = provider
        self._max_tokens = max_tokens

    def body(self, request: TalkerRequest) -> dict[str, object]:
        system = {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": request.prefix.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                system,
                *({"role": m.role, "content": m.content} for m in request.messages),
            ],
            "provider": {"order": [self._provider], "allow_fallbacks": False},
            "reasoning": {"enabled": False},
        }

    async def reply(self, request: TalkerRequest) -> Reply:
        started = time.perf_counter()
        resp = await self._client.post(
            URL,
            headers={"authorization": f"Bearer {self._key}"},
            json=self.body(request),
            timeout=60,
        )
        resp.raise_for_status()
        data = obj(resp.json())
        first = obj(seq(data.get("choices"))[0]) if seq(data.get("choices")) else {}
        text = string(obj(first.get("message")).get("content")).strip()
        usage = obj(data.get("usage"))
        details = obj(usage.get("prompt_tokens_details"))
        return Reply(
            text=text,
            model=string(data.get("model"), self._model),
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=integer(usage.get("prompt_tokens")),
            cache_read_tokens=integer(details.get("cached_tokens")),
            cache_write_tokens=integer(details.get("cache_write_tokens")),
        )
