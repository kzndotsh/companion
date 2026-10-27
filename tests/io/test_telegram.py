from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from companion.core.turn.quoted import Quoted
from companion.core.types import Speaker
from companion.io.surface import Hooks, Incoming, Surface
from companion.io.telegram import Telegram, TelegramError

ALLOWED = 42


def _update(
    text: str, user: int = ALLOWED, chat: int = ALLOWED, update_id: int = 1
) -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {"message_id": 99, "text": text, "from": {"id": user}, "chat": {"id": chat}},
    }


def _ok(calls: list[tuple[str, dict[str, object]]]) -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((str(req.url).rsplit("/", 1)[-1], json.loads(req.content)))
        return httpx.Response(200, json={"ok": True, "result": True})

    return httpx.MockTransport(handler)


def test_the_allowed_user_s_text_in_their_own_chat_comes_in() -> None:
    tg = Telegram("t", ALLOWED, httpx.AsyncClient())
    got, offset = tg.read([_update("hello")], 0)
    assert got == [Incoming("99", "hello", "1")]
    assert offset == 2


def test_a_message_sent_as_a_reply_says_which_one() -> None:
    tg = Telegram("t", ALLOWED, httpx.AsyncClient())
    update = _update("/flag")
    message = update["message"]
    assert isinstance(message, dict)
    message["reply_to_message"] = {"message_id": 42}
    got, _ = tg.read([update], 0)
    assert got == [Incoming("99", "/flag", "1", "42")]


def test_a_reply_carries_the_text_it_points_at_or_the_part_they_quoted() -> None:
    tg = Telegram("t", ALLOWED, httpx.AsyncClient())
    whole, part = _update("so cute"), _update("this bit", update_id=2)
    for update in (whole, part):
        message = update["message"]
        assert isinstance(message, dict)
        message["reply_to_message"] = {"message_id": 42, "text": "a. b.", "from": {"is_bot": True}}
    part_message = part["message"]
    assert isinstance(part_message, dict)
    part_message["quote"] = {"text": "b."}
    got, _ = tg.read([whole, part], 0)
    assert [m.quoted for m in got] == [
        Quoted("a. b.", Speaker.COMPANION),
        Quoted("b.", Speaker.COMPANION),
    ]


async def test_a_send_returns_the_id_of_the_message_sent() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 314}})

    tg = Telegram("t", ALLOWED, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert await tg.send("hello") == "314"


def test_other_users_group_chats_and_non_text_are_ignored() -> None:
    tg = Telegram("t", ALLOWED, httpx.AsyncClient())
    photo = {"update_id": 4, "message": {"message_id": 5, "from": {"id": ALLOWED}}}
    updates: list[object] = [
        _update("hello", user=999, update_id=1),
        _update("hello all", chat=-100, update_id=2),
        photo,
    ]
    got, offset = tg.read(updates, 0)
    assert got == []
    assert offset == 5  # each is still passed over, never fetched again


def test_an_update_handled_before_a_restart_is_not_handled_again() -> None:
    tg = Telegram("t", ALLOWED, httpx.AsyncClient())
    # after a restart the saved id (41) makes the next offset 42, and Telegram resends 41 anyway
    got, offset = tg.read([_update("first", update_id=41), _update("second", update_id=42)], 42)
    assert [m.text for m in got] == ["second"]
    assert got[0].cursor == "42"
    assert offset == 43


async def test_a_reaction_and_a_message_go_to_their_chat() -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    tg = Telegram("t", ALLOWED, httpx.AsyncClient(transport=_ok(calls)))
    await tg.react("99", "✍")
    await tg.send("hi")
    assert calls == [
        (
            "setMessageReaction",
            {"chat_id": ALLOWED, "message_id": 99, "reaction": [{"type": "emoji", "emoji": "✍"}]},
        ),
        ("sendMessage", {"chat_id": ALLOWED, "text": "hi"}),
    ]


async def test_a_failed_typing_indicator_does_not_lose_the_reply() -> None:
    sent: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        if method == "sendChatAction":
            return httpx.Response(500, json={"ok": False})
        if method == "sendMessage":
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    async def talk(text: str, _quoted: Quoted | None = None) -> str:
        del text
        await asyncio.sleep(0.05)  # long enough for the typing indicator to be tried
        return "reply"

    tg = Telegram("t", ALLOWED, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await Surface(tg, pace=0.01).reply_to(Incoming("99", "hi", "1"), talk, {})
    assert sent == ["reply"]


async def test_a_refused_send_reaches_the_surface_as_a_delivery_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(seconds: float) -> None:
        del seconds

    monkeypatch.setattr("companion.io.telegram.asyncio.sleep", no_sleep)

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(400, json={"ok": False})

    told: list[str] = []

    async def on_undelivered(text: str, reason: str, delivered: str) -> None:
        del delivered
        told.append(f"{text}: {reason}")

    async def talk(text: str, _quoted: Quoted | None = None) -> str:
        del text
        return "never seen"

    tg = await _tg(handler)
    surface = Surface(tg, Hooks(on_undelivered=on_undelivered))
    await surface.reply_to(Incoming("99", "hi", "1"), talk, {})
    assert told == ["never seen: telegram sendMessage failed with status 400"]


async def _tg(handler: object) -> Telegram:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return Telegram("SECRET:TOKEN", ALLOWED, client)


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
    await tg.send("hello")
    assert waits == [2.0]
    assert len(calls) == 2


async def test_a_rate_limit_waits_the_full_time_asked_until_the_budget_runs_out(
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
        return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 8}})

    tg = await _tg(handler)
    with pytest.raises(TelegramError):
        await tg.send("hello")
    assert waits == [8.0] * 7  # 56 s waited; another 8 would pass the 60 s budget
    assert len(calls) == 8  # no second round from the send's own retry


async def test_a_wait_longer_than_the_budget_gives_up_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import companion.io.telegram as module  # noqa: PLC0415

    waits: list[float] = []

    async def no_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)

    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 600}})

    tg = await _tg(handler)
    with pytest.raises(TelegramError):
        await tg.send("hello")
    assert waits == []


async def test_errors_never_carry_the_bot_token() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        del req
        return httpx.Response(500, json={"ok": False})

    tg = await _tg(handler)
    with pytest.raises(TelegramError) as caught:
        await tg.send("x")
    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


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

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tg = Telegram("t", ALLOWED, client)
    real_sleep = asyncio.sleep

    async def quick_sleep(seconds: float) -> None:
        await real_sleep(min(seconds, 0.01))

    with caplog.at_level(logging.INFO, logger="companion.telegram"):
        asyncio.sleep = quick_sleep  # type: ignore[assignment]
        try:
            task = asyncio.create_task(tg.receive(asyncio.Queue(), None))
            await real_sleep(0.2)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        finally:
            asyncio.sleep = real_sleep  # type: ignore[assignment]
    messages = [r.getMessage() for r in caplog.records]
    assert sum("poll failed" in m for m in messages) == 2
    assert "poll recovered after 2 failed attempt(s)" in messages
