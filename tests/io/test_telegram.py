from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx
import pytest

from companion.core.turn.ack import ReactAndReply, Reaction, ThenSend
from companion.io.telegram import Hooks, Telegram, TelegramError

ALLOWED = 42


def _update(text: str, user: int = ALLOWED) -> dict[str, object]:
    return {
        "update_id": 1,
        "message": {"message_id": 99, "text": text, "from": {"id": user}, "chat": {"id": 7}},
    }


@dataclass
class Seen:
    handled: list[str] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    reactions: list[dict[str, object]] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


async def _run(update: dict[str, object], *, reactions_fail: bool = False) -> Seen:
    seen = Seen()

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        seen.methods.append(method)
        body = json.loads(req.content)
        if method == "sendMessage":
            seen.sent.append(body["text"])
        if method == "setMessageReaction":
            if reactions_fail:
                return httpx.Response(400, json={"ok": False})
            seen.reactions.append(body)
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        seen.handled.append(text)
        return "reply"

    async def flag(arg: str) -> str | Reaction:
        seen.handled.append(f"FLAG:{arg}")
        return Reaction("✍")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await Telegram("t", ALLOWED, client).handle_update(update, talk, {"flag": flag})
    return seen


async def test_plain_text_goes_to_the_model() -> None:
    seen = await _run(_update("hello"))
    assert seen.handled == ["hello"]
    assert seen.sent == ["reply"]


async def test_flag_reacts_to_the_message_and_sends_no_text() -> None:
    seen = await _run(_update("/flag forgot you knew"))
    assert seen.handled == ["FLAG:forgot you knew"]
    assert seen.sent == []
    assert seen.reactions == [
        {"chat_id": 7, "message_id": 99, "reaction": [{"type": "emoji", "emoji": "✍"}]}
    ]


async def test_a_refused_reaction_falls_back_to_text() -> None:
    seen = await _run(_update("/flag too_much"), reactions_fail=True)
    assert seen.handled == ["FLAG:too_much"]
    assert seen.sent == ["noted"]


async def test_flag_with_bot_suffix_is_the_same_command() -> None:
    seen = await _run(_update("/flag@my_bot too_much"))
    assert seen.handled == ["FLAG:too_much"]


async def test_unknown_commands_and_start_are_ignored() -> None:
    for text in ("/start", "/nonsense"):
        seen = await _run(_update(text))
        assert seen.handled == []
        assert seen.sent == []
        assert seen.reactions == []


async def test_other_users_are_ignored() -> None:
    seen = await _run(_update("hello", user=999))
    assert seen.handled == []
    assert seen.methods == []


async def _both(*, reactions_fail: bool = False) -> Seen:
    seen = Seen()

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        body = json.loads(req.content)
        seen.methods.append(method)
        if method == "sendMessage":
            seen.sent.append(body["text"])
        if method == "setMessageReaction":
            if reactions_fail:
                return httpx.Response(400, json={"ok": False})
            seen.reactions.append(body)
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> ReactAndReply:
        seen.handled.append(text)
        return ReactAndReply(Reaction("😁"), "ha, fair")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await Telegram("t", ALLOWED, client).handle_update(_update("a joke"), talk, {})
    return seen


async def test_a_reaction_and_a_reply_are_both_sent_reaction_first() -> None:
    seen = await _both()
    assert seen.sent == ["ha, fair"]
    assert seen.reactions == [
        {"chat_id": 7, "message_id": 99, "reaction": [{"type": "emoji", "emoji": "😁"}]}
    ]
    assert seen.methods.index("setMessageReaction") < seen.methods.index("sendMessage")


async def test_a_refused_reaction_still_sends_the_reply() -> None:
    seen = await _both(reactions_fail=True)
    assert seen.sent == ["ha, fair"]


async def _tg(handler: object) -> Telegram:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return Telegram("SECRET:TOKEN", ALLOWED, client)


async def test_a_failed_typing_indicator_does_not_lose_the_reply() -> None:
    seen = Seen()

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "sendChatAction":
            return httpx.Response(500, json={"ok": False})
        if method == "sendMessage":
            seen.sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return "reply"

    tg = await _tg(handler)
    await tg.handle_update(_update("hi"), talk, {})
    assert seen.sent == ["reply"]


async def test_a_rate_limit_is_retried_once_after_the_wait_telegram_asked_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import companion.io.telegram as module  # noqa: PLC0415

    waits: list[float] = []

    async def no_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
    calls: list[int] = []

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 2}})
        return httpx.Response(200, json={"ok": True, "result": "done"})

    tg = await _tg(handler)
    await tg.send(1, "hello")
    assert waits == [2.0]
    assert len(calls) == 2


async def test_errors_never_carry_the_bot_token() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(500, json={"ok": False})

    tg = await _tg(handler)
    with pytest.raises(TelegramError) as caught:
        await tg.send(1, "x")
    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


async def test_a_failed_send_does_not_stop_the_bot() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "sendMessage":
            return httpx.Response(400, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return "reply"

    tg = await _tg(handler)
    await tg.handle_update(_update("hi"), talk, {})  # must not raise


async def test_an_undelivered_reply_is_reported_with_its_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import companion.io.telegram as module  # noqa: PLC0415

    async def no_sleep(seconds: float) -> None:
        del seconds

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
    told: list[tuple[str, str]] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        assert delivered == ""
        told.append((text, reason))

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "sendMessage":
            return httpx.Response(500, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return "you never see this"

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await Telegram("T", ALLOWED, client, Hooks(on_undelivered=on_undelivered)).handle_update(
        _update("hi"), talk, {}
    )
    assert [t for t, _ in told] == ["you never see this"]
    assert "SECRET" not in told[0][1]


async def test_a_reply_cut_off_after_its_first_part_reports_the_part_that_arrived(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import companion.io.telegram as module  # noqa: PLC0415

    async def no_sleep(seconds: float) -> None:
        del seconds

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)

    def two_parts(text: str, *_: float) -> list[str]:
        del text
        return ["First bit.", "Second bit."]

    monkeypatch.setattr(module, "split_reply", two_parts)
    told: list[tuple[str, str]] = []
    sends = 0

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del reason
        told.append((text, delivered))

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal sends
        if str(req.url).endswith("sendMessage"):
            sends += 1
            if sends >= 2:  # the second part fails, retry included
                return httpx.Response(500, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return "First bit. Second bit."

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await Telegram(
        "T", ALLOWED, client, Hooks(on_undelivered=on_undelivered), pace=0.0, split=True
    ).handle_update(_update("hi"), talk, {})
    assert told == [("First bit. Second bit.", "First bit.")]


async def test_a_delivered_reply_is_not_reported() -> None:
    told: list[str] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        told.append(text + reason + delivered)

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return "fine"

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await Telegram("T", ALLOWED, client, Hooks(on_undelivered=on_undelivered)).handle_update(
        _update("hi"), talk, {}
    )
    assert told == []


async def test_an_update_handled_before_a_restart_is_not_handled_again() -> None:
    marked: list[int] = []
    handled: list[str] = []

    async def talk(text: str) -> str:
        handled.append(text)
        return "ok"

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(200, json={"ok": True, "result": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("T", ALLOWED, client, Hooks(mark_handled=marked.append))
    first = {**_update("first"), "update_id": 41}
    second = {**_update("second"), "update_id": 42}
    # after a restart the saved id (41) makes the next offset 42, and Telegram resends 41 anyway
    offset = await tg.process([first, second], 42, talk, {})
    assert handled == ["second"]
    assert marked == [42]
    assert offset == 43


async def test_updates_are_recorded_before_the_turn_runs_and_in_order() -> None:
    order: list[str] = []

    async def talk(text: str) -> str:
        order.append(f"turn {text}")
        return "ok"

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(200, json={"ok": True, "result": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("T", ALLOWED, client, Hooks(mark_handled=lambda i: order.append(f"mark {i}")))
    a = {**_update("a"), "update_id": 1}
    b = {**_update("b"), "update_id": 2}
    assert await tg.process([a, b], 0, talk, {}) == 3
    assert order == ["mark 1", "turn a", "mark 2", "turn b"]


async def _paced(
    reply: str | Reaction | ReactAndReply, pace: float, monkeypatch: pytest.MonkeyPatch
) -> tuple[list[str], list[float]]:
    """The calls Telegram saw, in order, and every sleep, with the clock and jitter pinned."""
    calls: list[str] = []
    sleeps: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url).rsplit("/", 1)[-1])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        calls.append(f"sleep {seconds:g}")

    async def talk(text: str) -> str | Reaction | ReactAndReply:
        del text
        return reply

    monkeypatch.setattr("companion.io.telegram.asyncio.sleep", fake_sleep)

    def steady(low: float, high: float) -> float:
        del low, high
        return 1.0

    monkeypatch.setattr("companion.io.telegram.random.uniform", steady)
    monkeypatch.setattr("companion.io.telegram.time.monotonic", lambda: 100.0)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client, pace=pace)
    await tg.handle_update(_update("hello there"), talk, {})
    return calls, sleeps


async def test_a_text_reply_waits_while_typing_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced("a reply of about seven words in total", 1.0, monkeypatch)
    assert sum(sleeps) > 0
    assert calls.index("sendMessage") > max(i for i, c in enumerate(calls) if c.startswith("sleep"))
    assert calls.count("sendChatAction") >= 2  # once at the start, once while waiting


async def test_pace_off_sends_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, sleeps = await _paced("a reply", 0.0, monkeypatch)
    assert sleeps == []
    assert calls == ["sendChatAction", "sendMessage"]


async def test_a_long_wait_keeps_the_typing_indicator_alive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced("word " * 60, 1.6, monkeypatch)
    assert len(sleeps) >= 2
    assert max(sleeps) <= 4.0
    assert calls.count("sendChatAction") >= len(sleeps)


async def test_a_reaction_reply_is_not_held_long_and_shows_no_typing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, sleeps = await _paced(Reaction("👍"), 1.0, monkeypatch)
    assert calls.count("sendChatAction") == 1
    assert 0 < sum(sleeps) < 3
    assert calls[-1] == "setMessageReaction"


async def test_the_reaction_comes_first_and_the_reply_after_its_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _ = await _paced(ReactAndReply(Reaction("❤"), "a reply here"), 1.0, monkeypatch)
    assert calls.index("setMessageReaction") < calls.index("sendMessage")
    sleep_at = [i for i, c in enumerate(calls) if c.startswith("sleep")]
    assert calls.index("setMessageReaction") < min(sleep_at) < calls.index("sendMessage")


async def test_a_command_reply_is_never_held(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async def flag(arg: str) -> str:
        del arg
        return "done"

    monkeypatch.setattr("companion.io.telegram.asyncio.sleep", fake_sleep)

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(200, json={"ok": True, "result": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client, pace=1.6)
    await tg.handle_update(_update("/flag"), flag, {"flag": flag})  # type: ignore[arg-type]
    assert sleeps == []


_LONG_REPLY = (
    "A lot of it is learned association: the smell is tied to waking up, comfort, and that first "
    "quiet moment of the day. Plus the aroma itself is rich and complex, so your brain gets a "
    "little reward before you even drink it."
)


async def _split_run(
    reply: str, *, split: bool, roll: float, fail_second_send: bool = False, pace: float = 0.0
) -> tuple[list[str], list[str]]:
    """The messages Telegram was asked to send, and every call in order."""
    sent: list[str] = []
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        calls.append(method)
        if method == "sendMessage":
            if fail_second_send and sent:
                return httpx.Response(500, json={"ok": False})
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        return reply

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client, pace=pace, split=split)
    import companion.io.telegram as module  # noqa: PLC0415

    original = module.random.random
    module.random.random = lambda: roll  # type: ignore[assignment]
    try:
        await tg.handle_update(_update("hi"), talk, {})
    finally:
        module.random.random = original
    return sent, calls


async def test_a_long_reply_is_sent_as_two_messages_with_the_same_words() -> None:
    sent, _ = await _split_run(_LONG_REPLY, split=True, roll=0.0)
    assert len(sent) == 2
    assert " ".join(sent) == _LONG_REPLY


async def test_split_off_or_a_high_roll_sends_one_message() -> None:
    assert (await _split_run(_LONG_REPLY, split=False, roll=0.0))[0] == [_LONG_REPLY]
    assert (await _split_run(_LONG_REPLY, split=True, roll=0.99))[0] == [_LONG_REPLY]


async def test_a_short_reply_is_never_split() -> None:
    assert (await _split_run("sounds good, talk soon.", split=True, roll=0.0))[0] == [
        "sounds good, talk soon."
    ]


async def test_a_failed_later_part_is_not_reported_as_an_undelivered_reply() -> None:
    sent, _ = await _split_run(_LONG_REPLY, split=True, roll=0.0, fail_second_send=True)
    assert len(sent) == 1  # the first part arrived, the second was refused, nothing crashed


async def test_each_part_waits_and_shows_typing_before_it_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url).rsplit("/", 1)[-1])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def fake_sleep(seconds: float) -> None:
        del seconds
        calls.append("sleep")

    async def talk(text: str) -> str:
        del text
        return _LONG_REPLY

    monkeypatch.setattr("companion.io.telegram.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("companion.io.telegram.random.random", lambda: 0.0)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await Telegram("t", ALLOWED, client, pace=1.0, split=True).handle_update(
        _update("hi"), talk, {}
    )
    sends = [i for i, c in enumerate(calls) if c == "sendMessage"]
    assert len(sends) == 2
    between = calls[sends[0] + 1 : sends[1]]
    assert "sleep" in between
    assert "sendChatAction" in between


def _msg(update_id: int, text: str) -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 100 + update_id,
            "text": text,
            "from": {"id": ALLOWED},
            "chat": {"id": 7},
        },
    }


async def _burst(
    first_reply: str, *, hold_pace: float, gap: float
) -> tuple[list[str], list[str], list[str]]:
    """Run the real polling loop with two messages `gap` seconds apart. Returns what was handled,
    what was sent, and the replies reported undelivered."""
    import asyncio  # noqa: PLC0415

    handled: list[str] = []
    sent: list[str] = []
    undelivered: list[str] = []
    batches = [[_msg(1, "first")], [_msg(2, "second")]]

    async def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "getUpdates":
            if batches:
                if len(batches) == 1:
                    await asyncio.sleep(gap)
                return httpx.Response(200, json={"ok": True, "result": batches.pop(0)})
            await asyncio.sleep(0.05)
            return httpx.Response(200, json={"ok": True, "result": []})
        if method == "sendMessage":
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

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

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram(
        "t", ALLOWED, client, Hooks(on_undelivered=on_undelivered), pace=hold_pace, split=False
    )
    task = asyncio.create_task(tg.run(talk, {}))
    await asyncio.sleep(gap + 1.2)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    return handled, sent, undelivered


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


async def test_a_recovered_poll_says_so_in_the_log(caplog: pytest.LogCaptureFixture) -> None:
    import asyncio  # noqa: PLC0415
    import logging  # noqa: PLC0415

    calls = 0

    async def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        if str(req.url).endswith("getUpdates"):
            calls += 1
            if calls <= 2:
                return httpx.Response(502, json={"ok": False, "description": "Bad Gateway"})
            await asyncio.sleep(0.02)
            return httpx.Response(200, json={"ok": True, "result": []})
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        return text

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client)
    real_sleep = asyncio.sleep

    async def quick_sleep(seconds: float) -> None:
        await real_sleep(min(seconds, 0.01))

    with caplog.at_level(logging.INFO, logger="companion.telegram"):
        asyncio.sleep = quick_sleep  # type: ignore[assignment]
        try:
            task = asyncio.create_task(tg.run(talk, {}))
            await real_sleep(0.2)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        finally:
            asyncio.sleep = real_sleep  # type: ignore[assignment]
    messages = [r.getMessage() for r in caplog.records]
    assert sum("poll failed" in m for m in messages) == 2
    assert "poll recovered after 2 failed attempt(s)" in messages


async def test_a_stop_lets_the_reply_in_progress_go_out_and_takes_nothing_new() -> None:
    import asyncio  # noqa: PLC0415

    sent: list[str] = []
    polls = 0
    stop = asyncio.Event()

    async def handler(req: httpx.Request) -> httpx.Response:
        nonlocal polls
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "getUpdates":
            polls += 1
            if polls == 1:
                return httpx.Response(200, json={"ok": True, "result": [_msg(1, "hey")]})
            await asyncio.sleep(0.05)
            return httpx.Response(200, json={"ok": True, "result": []})
        if method == "sendMessage":
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> str:
        del text
        stop.set()  # the stop comes while this reply is being written
        await asyncio.sleep(0.3)
        return "still answered"

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client, Hooks(), pace=0.0, split=False)
    await asyncio.wait_for(tg.run(talk, {}, stop), timeout=5)
    assert sent == ["still answered"]


async def _then(fail_first: bool, monkeypatch: pytest.MonkeyPatch) -> tuple[list[str], list[str]]:
    import companion.io.telegram as module  # noqa: PLC0415

    async def no_sleep(seconds: float) -> None:
        del seconds

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
    sent: list[str] = []
    told: list[str] = []
    calls = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "sendMessage":
            calls += 1
            if fail_first and calls <= 2:  # the reply and its one retry
                return httpx.Response(400, json={"ok": False})
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str) -> ThenSend:
        del text
        return ThenSend("i'm here", "the fixed line")

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del reason, delivered
        told.append(text)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("T", ALLOWED, client, Hooks(on_undelivered=on_undelivered), pace=0)
    await tg.handle_update(_update("hi"), talk, {})
    return sent, told


async def test_code_s_own_message_goes_after_the_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    sent, told = await _then(False, monkeypatch)
    assert sent == ["i'm here", "the fixed line"]
    assert told == []


async def test_code_s_own_message_still_goes_when_the_reply_could_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent, told = await _then(True, monkeypatch)
    assert sent == ["the fixed line"]
    assert told == ["i'm here"]
