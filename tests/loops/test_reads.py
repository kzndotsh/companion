from __future__ import annotations

from companion.core.agreement import unanimous
from companion.core.extractor import Extraction
from companion.core.types import Json
from companion.loops.reads import read_times


class Flaky:
    """Answers in turn from a script; an exception in the script is raised."""

    def __init__(self, *answers: Json | Exception) -> None:
        self.answers = list(answers)

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return Extraction(answer, "m", 0.01, 1)


A: Json = {"label": "a"}
NOPE: Json = {"nope": 1}


def _label(data: Json) -> str | None:
    value = data.get("label") if isinstance(data, dict) else None
    return value if isinstance(value, str) else None


async def test_every_read_answers() -> None:
    got = await read_times(Flaky(A, A, A), "s", "u", {}, _label, spend="t")
    assert got.values == ("a", "a", "a")
    assert not got.failed
    assert round(got.cost_usd, 2) == 0.03
    assert got.model == "m"


async def test_a_failed_call_or_an_unreadable_answer_is_a_none_read() -> None:
    got = await read_times(Flaky(A, RuntimeError("down"), NOPE), "s", "u", {}, _label, spend="t")
    assert got.values == ("a", None, None)
    assert got.failed
    assert round(got.cost_usd, 2) == 0.02  # the unreadable answer was still paid for


def test_agreement_needs_every_read_and_never_counts_a_failed_one() -> None:
    assert unanimous(["a", "a", "a"]) == "a"
    assert unanimous(["a", "a", None]) is None
    assert unanimous(["a", "b", "a"]) is None
    assert unanimous(["a", "a"]) is None
