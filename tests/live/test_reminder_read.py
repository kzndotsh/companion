"""Does the reminder read, with code's time rules, land each request at the time a person meant?

Run on purpose: `uv run pytest -m live tests/live/test_reminder_read.py -s`. Costs a few cents. The
requests are invented and describe no one. It is Monday 19 Oct 2026, 13:00 in New York. Each case
lists the outcomes that are right: a local time, "ask" (code asks instead of guessing), "none" or
"cancel".
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from companion.core.reminders import PROMPT, SCHEMA, Ask, parse, read_prompt, resolve
from companion.core.types import (
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.daemon import load_dotenv
from companion.models.openrouter import OpenRouterExtractor

pytestmark = pytest.mark.live

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 19, 17, 0, tzinfo=UTC)

CASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("remind me at 8pm to take the dog out", ("10-19 20:00",)),
    ("remind me in 20 minutes to check the oven", ("10-19 13:20",)),
    ("remind me in 2 hours to call the bank", ("10-19 15:00",)),
    ("remind me tomorrow at 9am about the dentist", ("10-20 09:00",)),
    ("can you remind me tonight to send the email", ("10-19 20:00",)),
    ("remind me friday at 6pm to buy wine", ("10-23 18:00",)),
    ("remind me next friday to buy wine", ("ask",)),
    ("remind me at 8 to take my pills", ("10-19 20:00", "ask")),
    ("remind me tomorrow at 8 to take my pills", ("ask",)),
    ("remind me tomorrow morning at 8 to take my pills", ("10-20 08:00",)),
    ("check up on me in a few days about the interview", ("10-22 18:00",)),
    ("check in on me tomorrow about how the exam went", ("10-20 18:00",)),
    ("ping me at 3:30 to leave for pickup", ("10-19 15:30",)),
    ("remind me every day at 9am to stretch", ("ask",)),
    ("remind me on november 2 at 9am to renew my passport", ("11-02 09:00",)),
    ("remind me at 20:00 to water the plants", ("10-19 20:00",)),
    ("remind me in 3 days to return the package", ("ask",)),
    ("remind me this evening to call mum", ("10-19 18:00",)),
    ("remind me tomorrow afternoon to pick up the dry cleaning", ("10-20 15:00",)),
    ("dont let me forget to text sam back at 5", ("10-19 17:00",)),
    ("i'll remember to call her, dont worry", ("none",)),
    ("remember that my sister's name is ana", ("none",)),
    ("im going to the gym at 6", ("none",)),
    ("my mom always reminds me to drink water lol", ("none",)),
    ("cancel the reminder about the dog", ("cancel",)),
    ("nvm dont remind me about the wine", ("cancel",)),
    ("remind me at 9am to call the vet", ("10-20 09:00",)),
    ("remind me in half an hour to flip the laundry", ("10-19 13:30",)),
    ("can you remind me on saturday morning to call grandma", ("10-24 09:00",)),
    ("remind me monday at 10am to submit the form", ("10-26 10:00",)),
    ("remind me at noon tomorrow to eat lunch", ("10-20 12:00",)),
    ("remind me in 90 days to renew the gym", ("ask",)),
    ("text me at 11pm to go to sleep", ("10-19 23:00",)),
    ("remind me later to do the dishes", ("ask",)),
    ("wanna remind me to stretch at 7 tonight?", ("10-19 19:00",)),
    ("check back in with me next week about the apartment", ("ask", "10-26 18:00")),
    ("remind me at 7 am tomorrow to leave early for the airport", ("10-20 07:00",)),
    ("remind me in an hour to take the bread out", ("10-19 14:00",)),
    ("set a reminder for 4:15 to join the call", ("10-19 16:15",)),
    ("you remind me of my cousin honestly", ("none",)),
)


def _said(text: str, speaker: Speaker, n: int) -> Utterance:
    return Utterance(
        UtteranceId(f"u{n}"),
        RelationshipId("r"),
        SessionId("s"),
        TurnId(f"t{n}"),
        speaker,
        text,
        Frame.REAL,
        "t",
        NOW,
    )


def _outcome(data: object) -> str:
    s = parse(data)  # type: ignore[arg-type]
    if s is None or s.ask is Ask.NONE:
        return "none"
    if s.ask is Ask.CANCEL:
        return "cancel"
    if s.repeats:
        return "ask"
    when = resolve(s, NOW, TZ)
    return "ask" if when.at is None else when.at.astimezone(TZ).strftime("%m-%d %H:%M")


async def test_requests_land_at_the_time_meant_and_ordinary_talk_sets_nothing() -> None:
    load_dotenv(Path(".env"))
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    prior = [_said("hey you", Speaker.COMPANION, 0)]
    asked = [
        _said("remind me to call mum", Speaker.USER, 1),
        _said("sure, what time?", Speaker.COMPANION, 2),
    ]
    cases = [(text, prior, ok) for text, ok in CASES] + [("8pm", asked, ("10-19 20:00",))]
    wrong: list[str] = []
    async with httpx.AsyncClient(timeout=60) as client:
        extractor = OpenRouterExtractor(key, client, "anthropic/claude-haiku-5.5")
        for text, before, ok in cases:
            result = await extractor.extract(
                PROMPT.text, read_prompt(before, text, NOW, TZ), SCHEMA
            )
            got = _outcome(result.data)
            if got not in ok:
                wrong.append(f"{text!r}: {got} (wanted {' or '.join(ok)}) {result.data}")
    print(f"\n{len(cases) - len(wrong)}/{len(cases)} right")  # noqa: T201
    for w in wrong:
        print("  ", w)  # noqa: T201
    false_sets = [w for w in wrong if "wanted none" in w and ": none" not in w]
    assert not false_sets, "ordinary talk must never set a reminder"
    assert len(wrong) <= 3
