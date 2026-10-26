from __future__ import annotations

import asyncio

import pytest

from companion.core.turn.ack import ReactAndReply, Reaction, ThenSend
from companion.io.surface import Hooks, Incoming, Reply, Surface
from tests.io.fake import Fake, msg


async def _talk_reply(text: str) -> str:
    del text
    return "reply"


async def _one(
    text: str, reply: Reply = "reply", *, react_fails: bool = False
) -> tuple[Fake, list[str]]:
    fake = Fake(react_fails=react_fails)
    handled: list[str] = []

    async def talk(t: str) -> Reply:
        handled.append(t)
        return reply

    async def flag(arg: str) -> str | Reaction:
        handled.append(f"FLAG:{arg}")
        return Reaction("✍")

    await Surface(fake).reply_to(msg(text), talk, {"flag": flag})
    return fake, handled


async def test_plain_text_goes_to_the_model() -> None:
    fake, handled = await _one("hello")
    assert handled == ["hello"]
    assert fake.sent == ["reply"]


async def test_flag_reacts_to_the_message_and_sends_no_text() -> None:
    fake, handled = await _one("/flag forgot you knew")
    assert handled == ["FLAG:forgot you knew"]
    assert fake.sent == []
    assert fake.reactions == ["99 ✍"]


async def test_a_refused_reaction_falls_back_to_text() -> None:
    fake, handled = await _one("/flag too_much", react_fails=True)
    assert handled == ["FLAG:too_much"]
    assert fake.sent == ["noted"]


async def test_flag_with_bot_suffix_is_the_same_command() -> None:
    _, handled = await _one("/flag@my_bot too_much")
    assert handled == ["FLAG:too_much"]


async def test_unknown_commands_and_start_are_ignored() -> None:
    for text in ("/start", "/nonsense"):
        fake, handled = await _one(text)
        assert handled == []
        assert fake.calls == []


async def test_a_reaction_and_a_reply_are_both_sent_reaction_first() -> None:
    fake, _ = await _one("a joke", ReactAndReply(Reaction("😁"), "ha, fair"))
    assert fake.calls == ["react 99 😁", "send ha, fair"]


async def test_a_refused_reaction_still_sends_the_reply() -> None:
    fake, _ = await _one("a joke", ReactAndReply(Reaction("😁"), "ha, fair"), react_fails=True)
    assert fake.sent == ["ha, fair"]


async def test_a_failed_send_does_not_stop_the_bot() -> None:
    fake = Fake(refuse=lambda n: True)
    await Surface(fake).reply_to(msg("hi"), _talk_reply, {})  # must not raise
    assert fake.sent == []


async def test_an_undelivered_reply_is_reported_with_its_text() -> None:
    told: list[tuple[str, str, str]] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        told.append((text, reason, delivered))

    async def talk(text: str) -> str:
        del text
        return "you never see this"

    fake = Fake(refuse=lambda n: True)
    await Surface(fake, Hooks(on_undelivered=on_undelivered)).reply_to(msg("hi"), talk, {})
    assert told == [("you never see this", "send refused", "")]


async def test_a_reply_cut_off_after_its_first_part_reports_the_part_that_arrived(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def two_parts(text: str, *_: float) -> list[str]:
        del text
        return ["First bit.", "Second bit."]

    monkeypatch.setattr("companion.io.surface.split_reply", two_parts)
    told: list[tuple[str, str]] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del reason
        told.append((text, delivered))

    async def talk(text: str) -> str:
        del text
        return "First bit. Second bit."

    fake = Fake(refuse=lambda n: n >= 2)
    surface = Surface(fake, Hooks(on_undelivered=on_undelivered), split=True)
    await surface.reply_to(msg("hi"), talk, {})
    assert fake.sent == ["First bit."]
    assert told == [("First bit. Second bit.", "First bit.")]


async def test_a_delivered_reply_is_not_reported() -> None:
    told: list[str] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        told.append(text + reason + delivered)

    fake = Fake()
    await Surface(fake, Hooks(on_undelivered=on_undelivered)).reply_to(msg("hi"), _talk_reply, {})
    assert told == []


async def test_messages_are_recorded_before_the_turn_runs_and_in_order() -> None:
    order: list[str] = []

    async def talk(text: str) -> str:
        order.append(f"turn {text}")
        return "ok"

    fake = Fake(script=[(0.0, Incoming("1", "a", "11")), (0.3, Incoming("2", "b", "12"))])
    surface = Surface(fake, Hooks(last_handled=lambda: "10", mark_handled=order.append))
    task = asyncio.create_task(surface.run(talk, {}))
    await asyncio.sleep(0.5)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert fake.after == ["10"]  # the transport resumes past the last handled message
    assert order == ["11", "turn a", "12", "turn b"]


async def test_a_transport_that_fails_stops_the_run_with_its_error() -> None:
    class Broken(Fake):
        async def receive(self, inbox: asyncio.Queue[Incoming], after: str | None) -> None:
            del inbox, after
            msg = "login refused"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="login refused"):
        await asyncio.wait_for(Surface(Broken()).run(_talk_reply, {}), timeout=2)


async def _paced(
    reply: Reply, pace: float, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[str], list[float]]:
    """The transport's calls, in order, and every sleep, with the clock and jitter pinned."""
    fake = Fake()
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        fake.calls.append(f"sleep {seconds:g}")

    async def talk(text: str) -> Reply:
        del text
        return reply

    monkeypatch.setattr("companion.io.surface.asyncio.sleep", fake_sleep)

    def steady(low: float, high: float) -> float:
        del low, high
        return 1.0

    monkeypatch.setattr("companion.io.surface.random.uniform", steady)
    monkeypatch.setattr("companion.io.surface.time.monotonic", lambda: 100.0)
    await Surface(fake, pace=pace).reply_to(msg("hello there"), talk, {})
    return [c.split(" ", 1)[0] if not c.startswith("sleep") else c for c in fake.calls], sleeps


async def test_a_text_reply_waits_while_typing_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced("a reply of about seven words in total", 1.0, monkeypatch)
    assert sum(sleeps) > 0
    assert calls.index("send") > max(i for i, c in enumerate(calls) if c.startswith("sleep"))
    assert "typing" in calls


async def test_the_reading_pause_shows_no_typing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, _ = await _paced("a reply of about seven words in total", 1.0, monkeypatch)
    first_sleep = next(i for i, c in enumerate(calls) if c.startswith("sleep"))
    assert first_sleep < calls.index("typing")


async def _typing_while_writing(writing: float, reply: str | Reaction) -> list[str]:
    """Real time: a pace whose reading pause is about 0.04 s, and a model that takes `writing`."""
    fake = Fake()

    async def talk(text: str) -> str | Reaction:
        del text
        await asyncio.sleep(writing)
        fake.calls.append("written")
        return reply

    await Surface(fake, pace=0.05).reply_to(msg("hello there"), talk, {})
    return fake.calls


async def test_typing_shows_while_a_slow_reply_is_written_once_the_reading_pause_is_over() -> None:
    calls = await _typing_while_writing(0.3, "sure")
    assert calls.index("typing") < calls.index("written")


async def test_a_reaction_ready_within_the_reading_pause_never_shows_typing() -> None:
    calls = await _typing_while_writing(0.0, Reaction("👍"))
    assert "typing" not in calls
    assert calls[-1] == "react 99 👍"


async def test_pace_off_sends_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, sleeps = await _paced("a reply", 0.0, monkeypatch)
    assert sleeps == []
    assert calls[-1] == "send"


async def test_a_long_wait_keeps_the_typing_indicator_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced("word " * 60, 1.6, monkeypatch)
    assert len(sleeps) >= 2
    assert max(sleeps) <= 4.0
    assert calls.count("typing") >= len(sleeps) - 1  # all but the reading pause


async def test_a_reaction_reply_is_not_held_long_and_shows_no_typing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced(Reaction("👍"), 1.0, monkeypatch)
    assert "typing" not in calls
    assert 0 < sum(sleeps) < 3
    assert calls[-1] == "react"


async def test_the_reaction_comes_first_and_the_reply_after_its_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _ = await _paced(ReactAndReply(Reaction("❤"), "a reply here"), 1.0, monkeypatch)
    assert calls.index("react") < calls.index("send")
    sleep_at = [i for i, c in enumerate(calls) if c.startswith("sleep")]
    assert calls.index("react") < min(sleep_at) < calls.index("send")


async def test_a_command_reply_is_never_held(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async def flag(arg: str) -> str:
        del arg
        return "done"

    monkeypatch.setattr("companion.io.surface.asyncio.sleep", fake_sleep)
    fake = Fake()
    await Surface(fake, pace=1.6).reply_to(msg("/flag"), flag, {"flag": flag})
    assert sleeps == []
    assert fake.sent == ["done"]


_LONG_REPLY = (
    "A lot of it is learned association: the smell is tied to waking up, comfort, and that first "
    "quiet moment of the day. Plus the aroma itself is rich and complex, so your brain gets a "
    "little reward before you even drink it."
)


async def _split_run(
    reply: str,
    *,
    split: bool,
    roll: float,
    monkeypatch: pytest.MonkeyPatch,
    refuse_second: bool = False,
) -> list[str]:
    """The messages the transport was asked to send and did."""

    async def talk(text: str) -> str:
        del text
        return reply

    monkeypatch.setattr("companion.io.surface.random.random", lambda: roll)
    fake = Fake(refuse=lambda n: refuse_second and n >= 2)
    await Surface(fake, split=split).reply_to(msg("hi"), talk, {})
    return fake.sent


async def test_a_long_reply_is_sent_as_two_messages_with_the_same_words(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = await _split_run(_LONG_REPLY, split=True, roll=0.0, monkeypatch=monkeypatch)
    assert len(sent) == 2
    assert " ".join(sent) == _LONG_REPLY


async def test_split_off_or_a_high_roll_sends_one_message(monkeypatch: pytest.MonkeyPatch) -> None:
    off = await _split_run(_LONG_REPLY, split=False, roll=0.0, monkeypatch=monkeypatch)
    high = await _split_run(_LONG_REPLY, split=True, roll=0.99, monkeypatch=monkeypatch)
    assert off == high == [_LONG_REPLY]


async def test_a_short_reply_is_never_split(monkeypatch: pytest.MonkeyPatch) -> None:
    short = "sounds good, talk soon."
    assert await _split_run(short, split=True, roll=0.0, monkeypatch=monkeypatch) == [short]


async def test_a_failed_later_part_stops_the_rest_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent = await _split_run(
        _LONG_REPLY, split=True, roll=0.0, monkeypatch=monkeypatch, refuse_second=True
    )
    assert len(sent) == 1  # the first part arrived, the second was refused, nothing crashed


async def test_each_part_waits_and_shows_typing_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = Fake()

    async def fake_sleep(seconds: float) -> None:
        del seconds
        fake.calls.append("sleep")

    async def talk(text: str) -> str:
        del text
        return _LONG_REPLY

    monkeypatch.setattr("companion.io.surface.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("companion.io.surface.random.random", lambda: 0.0)
    await Surface(fake, pace=1.0, split=True).reply_to(msg("hi"), talk, {})
    sends = [i for i, c in enumerate(fake.calls) if c.startswith("send")]
    assert len(sends) == 2
    between = fake.calls[sends[0] + 1 : sends[1]]
    assert "sleep" in between
    assert "typing" in between


async def _burst(
    first_reply: str, *, hold_pace: float, gap: float
) -> tuple[list[str], list[str], list[str]]:
    """Run the real loop with two messages `gap` seconds apart. Returns what was handled, what was
    sent, and the replies reported undelivered."""
    handled: list[str] = []
    undelivered: list[str] = []
    fake = Fake(script=[(0.0, msg("first", 1)), (gap, msg("second", 2))])

    async def talk(text: str) -> str:
        handled.append(text)
        if text == "first":
            if first_reply == "":
                await asyncio.sleep(30)  # still being written when the next message arrives
            return first_reply
        return "reply to both"

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del reason, delivered
        undelivered.append(text)

    surface = Surface(fake, Hooks(on_undelivered=on_undelivered), pace=hold_pace)
    task = asyncio.create_task(surface.run(talk, {}))
    await asyncio.sleep(gap + 1.2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    return handled, fake.sent, undelivered


async def test_a_message_that_arrives_while_the_reply_is_being_written_replaces_it() -> None:
    handled, sent, undelivered = await _burst("", hold_pace=0.0, gap=0.2)
    assert handled == ["first", "second"]
    assert sent == ["reply to both"]
    assert undelivered == []  # nothing had been written, so nothing is marked


async def test_a_message_that_arrives_while_the_reply_is_held_replaces_it_and_marks_it() -> None:
    reply = "a reply long enough to be held for a little while before it goes out"
    handled, sent, undelivered = await _burst(reply, hold_pace=0.3, gap=0.15)
    assert handled == ["first", "second"]
    assert sent == ["reply to both"]
    assert undelivered == [reply]


async def test_messages_far_apart_are_each_answered() -> None:
    handled, sent, undelivered = await _burst("answer one", hold_pace=0.0, gap=0.6)
    assert handled == ["first", "second"]
    assert sent == ["answer one", "reply to both"]
    assert undelivered == []


async def test_a_stop_lets_the_reply_in_progress_go_out_and_takes_nothing_new() -> None:
    stop = asyncio.Event()
    fake = Fake(script=[(0.0, msg("hey", 1)), (0.1, msg("too late", 2))])

    async def talk(text: str) -> str:
        del text
        stop.set()  # the stop comes while this reply is being written
        await asyncio.sleep(0.3)
        return "still answered"

    await asyncio.wait_for(Surface(fake).run(talk, {}, stop), timeout=5)
    assert fake.sent == ["still answered"]


async def _then(refuse_first: bool) -> tuple[list[str], list[str]]:
    told: list[str] = []

    async def talk(text: str) -> ThenSend:
        del text
        return ThenSend("i'm here", "the fixed line")

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del reason, delivered
        told.append(text)

    fake = Fake(refuse=lambda n: refuse_first and n == 1)
    await Surface(fake, Hooks(on_undelivered=on_undelivered)).reply_to(msg("hi"), talk, {})
    return fake.sent, told


async def test_code_s_own_message_goes_after_the_reply() -> None:
    sent, told = await _then(False)
    assert sent == ["i'm here", "the fixed line"]
    assert told == []


async def test_code_s_own_message_still_goes_when_the_reply_could_not() -> None:
    sent, told = await _then(True)
    assert sent == ["the fixed line"]
    assert told == ["i'm here"]
