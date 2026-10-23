"""OpenRouter adapter for the talker. Provider is pinned, fallbacks off, reasoning off."""

from __future__ import annotations

import json
import logging
import time

import httpx

from companion.core.extractor import Extraction
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json
from companion.lib.retry import retry_on_network_error
from companion.models.wire import (
    integer,
    messages_with_breakpoint,
    number,
    obj,
    seq,
    string,
    system_blocks,
)

log = logging.getLogger("companion.openrouter")
URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-6-luna"
DEFAULT_PROVIDER = (
    "Anthropic"  # pinned only for anthropic/ models, so caching works; others route freely
)


def check(resp: httpx.Response, model: str) -> None:
    """Raise on an error status, after logging what OpenRouter said. The body names the cause
    (a provider outage, a bad key, no credit) and the bare status error does not."""
    if resp.status_code >= 400:
        log.warning("openrouter %s for %s: %s", resp.status_code, model, resp.text[:500])
    resp.raise_for_status()


class OpenRouterTalker:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        api_key: str,
        client: httpx.AsyncClient,
        model: str = DEFAULT_MODEL,
        provider: str = DEFAULT_PROVIDER,
        max_tokens: int = 400,
        reasoning_effort: str | None = None,
        timeout: float = 25,  # past this a reply is not coming; a backup model answers (J21)
    ) -> None:
        self._timeout = timeout
        self._key = api_key
        self._client = client
        self._model = model
        self._provider = provider
        self._max_tokens = max_tokens
        self._effort = reasoning_effort

    def body(self, request: TalkerRequest) -> dict[str, object]:
        system = {"role": "system", "content": system_blocks(request)}
        tail = [{"role": "system", "content": request.tail}] if request.tail else []
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [system, *messages_with_breakpoint(request), *tail],
            "reasoning": {"enabled": False}
            if self._effort is None
            else {"effort": self._effort, "exclude": True},
        }
        if self._model.startswith("anthropic/"):
            body["provider"] = {"order": [self._provider], "allow_fallbacks": False}
        return body

    async def reply(self, request: TalkerRequest) -> Reply:
        started = time.perf_counter()
        body = self.body(request)
        resp = await retry_on_network_error(
            lambda: self._client.post(
                URL,
                headers={"authorization": f"Bearer {self._key}"},
                json=body,
                timeout=self._timeout,
            ),
            what="talker",
        )
        check(resp, self._model)
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
            cost_usd=number(usage.get("cost")),
        )


class OpenRouterExtractor:
    """Structured output through a forced tool call. Never used on the talker request."""

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient,
        model: str = "anthropic/claude-haiku-5.5",
        provider: str = DEFAULT_PROVIDER,
        max_tokens: int = 2000,
    ) -> None:
        self._key = api_key
        self._client = client
        self._model = model
        self._provider = provider
        self._max_tokens = max_tokens

    def body(self, system: str, user: str, schema: dict[str, Json]) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "record",
                        "description": "Record the result.",
                        "parameters": schema,
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "record"}},
            "reasoning": {"enabled": False},
        }
        if self._model.startswith("anthropic/"):
            body["provider"] = {"order": [self._provider], "allow_fallbacks": False}
        return body

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        started = time.perf_counter()
        resp = await self._client.post(
            URL,
            headers={"authorization": f"Bearer {self._key}"},
            json=self.body(system, user, schema),
            timeout=120,
        )
        check(resp, self._model)
        data = obj(resp.json())
        first = obj(seq(data.get("choices"))[0]) if seq(data.get("choices")) else {}
        calls = seq(obj(first.get("message")).get("tool_calls"))
        args = string(obj(obj(calls[0]).get("function")).get("arguments")) if calls else ""
        parsed: Json = json.loads(args) if args else None
        usage = obj(data.get("usage"))
        return Extraction(
            data=parsed,
            model=string(data.get("model"), self._model),
            cost_usd=number(usage.get("cost")),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
