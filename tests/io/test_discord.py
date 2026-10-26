from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import discord
import pytest

from companion.io import discord as module
from companion.io.discord import Discord, DiscordError, connected
from companion.io.surface import Hooks, Incoming, Surface

ALLOWED = 42
BOT = 7
PRIVATE = discord.ChannelType.private


def _message(n: int, text: str = "hi", author: int = ALLOWED, kind: object = PRIVATE) -> Any:
    return SimpleNamespace(
        id=n, content=text, author=SimpleNamespace(id=author), channel=SimpleNamespace(type=kind)
    )


def _forbidden() -> discord.Forbidden:
    response = SimpleNamespace(status=403, reason="Forbidden")
    return discord.Forbidden(response, "Missing Access SECRET.TOKEN")  # type: ignore[arg-type]


@dataclass
class FakeDM:
    old: list[Any] = field(default_factory=list[Any])
    fail: BaseException | None = None
    during_history: Callable[[], Awaitable[None]] | None = None
    sent: list[str] = field(default_factory=list[str])
    reactions: list[tuple[int, str]] = field(default_factory=list[tuple[int, str]])

    async def send(self, text: str) -> None:
        if self.fail is not None:
            raise self.fail
        self.sent.append(text)

    def get_partial_message(self, message_id: int) -> Any:
        async def add_reaction(emoji: str) -> None:
            if self.fail is not None:
                raise self.fail
            self.reactions.append((message_id, emoji))

        return SimpleNamespace(add_reaction=add_reaction)

    async def typing(self) -> None:
        if self.fail is not None:
            raise self.fail

    async def history(self, *, after: discord.Object, oldest_first: bool, limit: None) -> Any:
        assert oldest_first
        assert limit is None
        for m in self.old:
            if m.id > after.id:
                yield m
                if self.during_history is not None:
                    await self.during_history()


class FakeClient:
    def __init__(self, dm: FakeDM) -> None:
        self.user = SimpleNamespace(id=BOT)
        self.dm = dm
        self.ready = asyncio.Event()
        self.closed = asyncio.Event()

    async def connect(self) -> None:
        self.ready.set()
        await self.closed.wait()

    async def wait_until_ready(self) -> None:
        await self.ready.wait()

    async def fetch_user(self, user_id: int) -> Any:
        assert user_id == ALLOWED

        async def create_dm() -> FakeDM:
            return self.dm

        return SimpleNamespace(create_dm=create_dm)


def _discord(dm: FakeDM | None = None) -> tuple[Discord, FakeDM]:
    dm = dm or FakeDM()
    return Discord(FakeClient(dm), ALLOWED), dm  # type: ignore[arg-type]


async def _received(dc: Discord, after: str | None, live: list[Any]) -> list[str]:
    """What `receive` queued once it is connected and `live` has come in."""
    inbox: asyncio.Queue[Incoming] = asyncio.Queue()
    task = asyncio.create_task(dc.receive(inbox, after))
    await asyncio.sleep(0.01)
    for m in live:
        await dc.on_message(m)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    return [inbox.get_nowait().text for _ in range(inbox.qsize())]


async def test_only_direct_messages_from_the_allowed_user_come_in() -> None:
    dc, _ = _discord()
    live = [
        _message(1, "from someone else", author=999),
        _message(2, "in a server", kind=discord.ChannelType.text),
        _message(3, "the bot itself", author=BOT),
        _message(4, "", author=ALLOWED),  # an attachment alone has no text
        _message(5, "hello"),
    ]
    assert await _received(dc, None, live) == ["hello"]


async def test_the_allowed_user_is_ignored_when_the_bot_is_that_user() -> None:
    dc, _ = _discord()
    dc._client.user = SimpleNamespace(id=ALLOWED)  # type: ignore[attr-defined]
    assert await _received(dc, None, [_message(5, "echo")]) == []


async def test_on_a_first_start_nothing_old_is_answered() -> None:
    dc, _ = _discord(FakeDM(old=[_message(1, "old")]))
    assert await _received(dc, None, [_message(2, "new")]) == ["new"]


async def test_missed_messages_come_first_and_one_seen_twice_is_queued_once() -> None:
    dm = FakeDM(old=[_message(99, "handled"), _message(101, "missed a"), _message(102, "missed b")])
    dc, _ = _discord(dm)
    arrivals = iter([_message(102, "missed b"), _message(103, "during catch-up")])

    async def live_arrival() -> None:
        m = next(arrivals, None)
        if m is not None:
            await dc.on_message(m)

    dm.during_history = live_arrival
    got = await _received(dc, "100", [_message(104, "later")])
    assert got == ["missed a", "missed b", "during catch-up", "later"]


async def test_a_message_answered_before_a_restart_is_not_answered_again() -> None:
    saved: dict[str, str] = {}
    answered: list[str] = []

    async def talk(text: str) -> str:
        answered.append(text)
        return "ok"

    async def run_once(dm: FakeDM) -> None:
        dc, _ = _discord(dm)
        hooks = Hooks(
            last_handled=lambda: saved.get("last"),
            mark_handled=lambda cursor: saved.__setitem__("last", cursor),
        )
        task = asyncio.create_task(Surface(dc, hooks).run(talk, {}))
        await asyncio.sleep(0.05)
        if not answered:
            await dc.on_message(_message(200, "first"))
            await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    await run_once(FakeDM())
    assert answered == ["first"]
    await run_once(FakeDM(old=[_message(200, "first"), _message(201, "while down")]))
    assert answered == ["first", "while down"]
    assert saved["last"] == "201"


async def test_a_long_reply_goes_out_as_messages_of_at_most_2000_characters() -> None:
    reply = "This sentence is part of a long reply. " * 64  # about 2500 characters
    assert len(reply) > 2400

    async def talk(text: str) -> str:
        del text
        return reply

    dc, dm = _discord()
    await Surface(dc).reply_to(Incoming("5", "hi", "5"), talk, {})
    assert len(dm.sent) == 2
    assert all(len(p) <= 2000 for p in dm.sent)
    assert " ".join(dm.sent).split() == reply.split()


async def test_a_reaction_goes_on_their_message() -> None:
    dc, dm = _discord()
    await dc.react("123", "✍")
    assert dm.reactions == [(123, "✍")]


async def test_errors_never_carry_the_token_and_typing_never_raises() -> None:
    dc, _ = _discord(FakeDM(fail=_forbidden()))
    for call in (dc.send("x"), dc.react("1", "✍")):
        with pytest.raises(DiscordError) as caught:
            await call
        assert "SECRET" not in str(caught.value)
        assert "403" in str(caught.value)
        assert caught.value.__cause__ is None
        assert caught.value.__suppress_context__
    await dc.typing()  # must not raise


async def test_a_typing_indicator_held_up_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "TYPING_SECONDS", 0.01)
    dc, dm = _discord()

    async def stuck() -> None:
        await asyncio.sleep(5)

    dm.typing = stuck  # type: ignore[method-assign]
    await asyncio.wait_for(dc.typing(), timeout=1)


async def test_a_refused_token_stops_with_an_error_that_does_not_carry_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def refuse(self: discord.Client, token: str) -> None:
        del self
        raise discord.LoginFailure(f"Improper token has been passed: {token}")

    monkeypatch.setattr(discord.Client, "login", refuse)
    with pytest.raises(DiscordError) as caught:
        async with connected("SECRET.TOKEN", ALLOWED):
            pass
    assert "SECRET" not in str(caught.value)
    assert caught.value.__cause__ is None


async def test_a_gateway_that_closes_stops_the_surface() -> None:
    dc, _ = _discord()
    client: FakeClient = dc._client  # type: ignore[assignment]

    async def closes() -> None:
        client.ready.set()

    client.connect = closes  # type: ignore[method-assign]

    async def talk(text: str) -> str:
        return text

    with pytest.raises(DiscordError, match="gateway closed"):
        await asyncio.wait_for(Surface(dc).run(talk, {}), timeout=1)
