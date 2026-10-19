from __future__ import annotations

import httpx
import pytest

from companion.core.extractor import Extraction, from_fallback
from companion.core.types import Json
from companion.models.fallback import RefusalFallback


class Refuses:
    def __init__(self, status: int) -> None:
        self.status = status

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(self.status, request=request)
        msg = "refused"
        raise httpx.HTTPStatusError(msg, request=request, response=response)


class Answers:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        return Extraction({"ok": True}, "second/model", 0.001, 5)


async def test_a_refused_call_goes_to_the_second_model_and_is_marked() -> None:
    got = await RefusalFallback(Refuses(403), Answers()).extract("s", "u", {})
    assert got.data == {"ok": True}
    assert from_fallback(got.model)


async def test_other_errors_are_raised_as_before() -> None:
    with pytest.raises(httpx.HTTPStatusError):
        await RefusalFallback(Refuses(500), Answers()).extract("s", "u", {})


async def test_an_answer_from_the_first_model_is_not_marked() -> None:
    got = await RefusalFallback(Answers(), Refuses(403)).extract("s", "u", {})
    assert not from_fallback(got.model)
