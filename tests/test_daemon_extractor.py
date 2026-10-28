"""The judges' extractor as the daemon builds it, against a fake OpenRouter: which model each call
names on the wire, and which answered."""

from __future__ import annotations

import json

import httpx
import pytest

from companion import daemon
from companion.core.extractor import FALLBACK
from companion.core.types import Speaker
from companion.features.crisis.run import read_risk
from companion.kit.reads import read_times
from companion.settings import Settings

DEEPSEEK = "deepseek/deepseek-v4.1-flash"
ANSWER = {
    "kind": "none",
    "literal": False,
    "timing": "hypothetical",
    "plan_or_means": False,
}


def _openrouter(asked: list[str], refuse: frozenset[str]) -> httpx.AsyncClient:
    def reply(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        asked.append(model)
        if model in refuse:
            return httpx.Response(403, json={"error": "moderation"})
        call = {"function": {"name": "record", "arguments": json.dumps(ANSWER)}}
        message = {"message": {"tool_calls": [call]}}
        return httpx.Response(200, json={"model": model, "choices": [message], "usage": {}})

    return httpx.AsyncClient(transport=httpx.MockTransport(reply))


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("COMPANION_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("COMPANION_JUDGE_STANDBY", raising=False)


async def test_by_default_the_risk_judge_reads_on_deepseek_and_haiku_answers_a_refusal() -> None:
    asked: list[str] = []
    routes = Settings.from_env({}).judge_routes
    async with _openrouter(asked, frozenset()) as client:
        got = await read_risk(daemon.extractor(client, routes), [(Speaker.USER, "hi")], "ugh")
    assert asked == [DEEPSEEK] * 3
    assert got.model == DEEPSEEK
    assert None not in got.values
    asked.clear()
    async with _openrouter(asked, frozenset({DEEPSEEK})) as client:
        got = await read_risk(daemon.extractor(client, routes), [], "ugh")
    assert asked.count(daemon.JUDGE_MODEL) == 3
    assert got.model == daemon.JUDGE_MODEL + FALLBACK


async def test_other_judges_stay_on_haiku_with_deepseek_behind_it() -> None:
    asked: list[str] = []
    routes = Settings.from_env({}).judge_routes
    async with _openrouter(asked, frozenset({daemon.JUDGE_MODEL})) as client:
        got = await read_times(
            daemon.extractor(client, routes), "s", "u", {}, lambda d: d, spend="worth", times=1
        )
    assert asked == [daemon.JUDGE_MODEL, daemon.JUDGE_STANDBY]
    assert got.model == daemon.JUDGE_STANDBY + FALLBACK
