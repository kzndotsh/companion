from __future__ import annotations

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.spend import MeteredExtractor, MeteredTalker, SpendEvent, purpose
from companion.core.talker import Reply
from companion.core.types import Json


class Talker:
    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        return Reply(text="hi", model="m-talk", latency_ms=1, input_tokens=300, cost_usd=0.002)


class Extractor:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        return Extraction(data=None, model="m-judge", cost_usd=0.0004, latency_ms=1)


REQUEST = TalkerRequest(build_prefix("x " * 3000), ())


async def test_a_talker_call_is_reported_with_its_cost_and_fixed_purpose() -> None:
    seen: list[SpendEvent] = []
    reply = await MeteredTalker(Talker(), seen.append, "scene talker").reply(REQUEST)
    assert reply.text == "hi"
    assert seen == [SpendEvent("scene talker", "m-talk", 0.002, 300)]


async def test_an_extractor_call_takes_the_purpose_the_judge_named() -> None:
    seen: list[SpendEvent] = []
    metered = MeteredExtractor(Extractor(), seen.append, "judge")
    with purpose("ack"):
        await metered.extract("s", "u", {})
    await metered.extract("s", "u", {})
    assert [e.purpose for e in seen] == ["ack", "judge"]
    assert all(e.cost_usd == 0.0004 and e.model == "m-judge" for e in seen)


async def test_the_purpose_does_not_leak_past_its_block() -> None:
    seen: list[SpendEvent] = []
    metered = MeteredExtractor(Extractor(), seen.append, "memory")
    with purpose("frame"):
        pass
    await metered.extract("s", "u", {})
    assert seen[0].purpose == "memory"
