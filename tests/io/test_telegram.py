from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx
import pytest

from companion.core.ack import ReactAndReply, Reaction
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

    async def on_undelivered(text: str, reason: str) -> None:
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


async def test_a_delivered_reply_is_not_reported() -> None:
    told: list[str] = []

    async def on_undelivered(text: str, reason: str) -> None:
        told.append(text + reason)

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
