"""OpenRouter embeddings, for the relevance look-up (`core/relevance.py`). Vectors come back unit
length, so a dot product is the cosine."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from companion.core.vectors import Embedded, unit
from companion.models.openrouter import check
from companion.models.wire import number, obj, seq

URL = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_MODEL = "openai/text-embedding-3-small"


class OpenRouterEmbedder:
    def __init__(self, key: str, client: httpx.AsyncClient, model: str = DEFAULT_MODEL) -> None:
        self._key, self._client, self._model = key, client, model

    async def embed(self, texts: Sequence[str]) -> Embedded:
        resp = await self._client.post(
            URL,
            headers={"Authorization": f"Bearer {self._key}"},
            json={"model": self._model, "input": list(texts)},
            timeout=30,
        )
        check(resp, self._model)
        data = obj(resp.json())
        rows = sorted((obj(r) for r in seq(data.get("data"))), key=lambda r: number(r.get("index")))
        vectors = tuple(unit([number(x) for x in seq(r.get("embedding"))]) for r in rows)
        if len(vectors) != len(texts):
            msg = f"asked for {len(texts)} embeddings, got {len(vectors)}"
            raise ValueError(msg)
        # the configured name, not the provider's short one, so stored vectors are found again
        return Embedded(vectors, self._model, number(obj(data.get("usage")).get("cost")))
