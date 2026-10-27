from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import discord
import pytest
from discord import app_commands

from companion.core.turn.ack import ReactAndReply, Reaction
from companion.core.turn.quoted import Quoted
from companion.core.types import Speaker
from companion.io import discord as module
from companion.io.discord import (
    FAILED,
    NOT_YOURS,
    Discord,
    DiscordError,
    _Marks,  # pyright: ignore[reportPrivateUsage]
    command_tree,
    connected,
    run_command,
    said,
)
from companion.io.surface import Commands, Hooks, Incoming, Surface

ALLOWED = 42
BOT = 7
PRIVATE = discord.ChannelType.private


def _message(n: int, text: str = "hi", author: int = ALLOWED, kind: object = PRIVATE) -> Any:
    return SimpleNamespace(
        id=n,
        content=text,
        author=SimpleNamespace(id=author),
        channel=SimpleNamespace(type=kind),
        reference=None,
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

    async def send(self, text: str) -> Any:
        if self.fail is not None:
            raise self.fail
        self.sent.append(text)
        return SimpleNamespace(id=1000 + len(self.sent))

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


async def test_a_new_session_after_a_dropped_connection_fetches_what_was_missed() -> None:
    dm = FakeDM()
    dc, _ = _discord(dm)
    inbox: asyncio.Queue[Incoming] = asyncio.Queue()
    task = asyncio.create_task(dc.receive(inbox, "100"))
    await asyncio.sleep(0.01)
    await dc.on_message(_message(101, "before the drop"))
    dm.old = [_message(101, "before the drop"), _message(102, "during the gap")]
    await dc.on_ready()
    await dc.on_message(_message(103, "after"))
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    got = [inbox.get_nowait().text for _ in range(inbox.qsize())]
    assert got == ["before the drop", "during the gap", "after"]


async def test_a_message_answered_before_a_restart_is_not_answered_again() -> None:
    saved: dict[str, str] = {}
    answered: list[str] = []

    async def talk(msg: Incoming) -> str:
        text = msg.text
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

    async def talk(msg: Incoming) -> str:
        text = msg.text
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

    async def talk(msg: Incoming) -> str:
        text = msg.text
        return text

    with pytest.raises(DiscordError, match="gateway closed"):
        await asyncio.wait_for(Surface(dc).run(talk, {}), timeout=1)


async def test_the_start_warnings_about_guilds_and_voice_are_silenced_and_others_are_not(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def accept(self: discord.Client, token: str) -> None:
        del self, token

    monkeypatch.setattr(discord.Client, "login", accept)
    monkeypatch.setattr(discord.VoiceClient, "warn_nacl", True)
    monkeypatch.setattr(discord.VoiceClient, "warn_dave", True)
    with caplog.at_level(logging.WARNING, logger="discord"):
        async with connected("TOKEN", ALLOWED):
            logging.getLogger("discord.state").warning("something else went wrong")
    warnings = [r.getMessage() for r in caplog.records]
    assert warnings == ["something else went wrong"]


async def test_a_dm_sent_as_a_reply_says_which_one_and_a_send_returns_its_id() -> None:
    dc, _ = _discord()
    inbox: asyncio.Queue[Incoming] = asyncio.Queue()
    task = asyncio.create_task(dc.receive(inbox, None))
    await asyncio.sleep(0.01)
    replying = _message(5, "/flag")
    replying.reference = _reply(1001, None)
    await dc.on_message(replying)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert inbox.get_nowait() == Incoming("5", "/flag", "5", "1001")
    assert await dc.send("hi") == "1001"


def _reply(message_id: int, resolved: object, kind: object = None) -> Any:
    return SimpleNamespace(
        message_id=message_id,
        type=kind or discord.MessageReferenceType.reply,
        resolved=resolved,
    )


@pytest.mark.parametrize(("author", "speaker"), [(BOT, Speaker.COMPANION), (ALLOWED, Speaker.USER)])
async def test_a_reply_carries_the_message_it_points_at_and_whose_it_was(
    author: int, speaker: Speaker
) -> None:
    dc, _ = _discord()
    inbox: asyncio.Queue[Incoming] = asyncio.Queue()
    task = asyncio.create_task(dc.receive(inbox, None))
    await asyncio.sleep(0.01)
    replying = _message(5, "so cute")
    replying.reference = _reply(3, _message(3, "your call, baby", author=author))
    await dc.on_message(replying)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    got = inbox.get_nowait()
    assert got.quoted == Quoted("your call, baby", speaker)


async def test_a_forward_or_a_deleted_message_carries_nothing_quoted() -> None:
    dc, _ = _discord()
    inbox: asyncio.Queue[Incoming] = asyncio.Queue()
    task = asyncio.create_task(dc.receive(inbox, None))
    await asyncio.sleep(0.01)
    forward = _message(5, "look")
    forward.reference = _reply(3, _message(3, "x"), discord.MessageReferenceType.forward)
    gone = _message(6, "that one")
    gone.reference = _reply(4, None)
    await dc.on_message(forward)
    await dc.on_message(gone)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert [inbox.get_nowait().quoted, inbox.get_nowait().quoted] == [None, None]


def _commands(seen: list[tuple[str, str, str | None]]) -> Commands:
    def named(name: str) -> Any:
        async def run(arg: str, replied_to: str | None) -> str | Reaction:
            seen.append((name, arg, replied_to))
            return Reaction("👎") if name == "flag" else "luna"

        return run

    return {"flag": named("flag"), "fav": named("fav"), "mode": named("mode")}


def test_the_tree_has_the_slash_commands_and_the_message_menu_in_dms_only() -> None:
    tree = command_tree(discord.Client(intents=discord.Intents.none()), ALLOWED, _commands([]))
    slash = {c.name for c in tree.get_commands(type=discord.AppCommandType.chat_input)}
    menu = {c.name for c in tree.get_commands(type=discord.AppCommandType.message)}
    assert slash == {"flag", "fav", "mode"}
    assert menu == {"Flag this", "Favorite this"}
    for command in tree.get_commands():
        assert isinstance(command, app_commands.Command | app_commands.ContextMenu)
        where = command.allowed_contexts
        assert where is not None
        assert (where.dm_channel, where.guild, where.private_channel) == (True, False, False)


def test_an_answer_reads_as_text() -> None:
    assert said(Reaction("👎")) == "👎"
    assert said(ReactAndReply(Reaction("💛"), "noted")) == "💛 noted"
    assert said("") == "done"


async def test_a_command_runs_by_name_and_a_failure_is_answered() -> None:
    seen: list[tuple[str, str, str | None]] = []
    assert await run_command(_commands(seen), "flag", "too long", "m1") == "👎"
    assert seen == [("flag", "too long", "m1")]

    async def broken(arg: str, replied_to: str | None) -> str:
        raise RuntimeError(arg)

    assert await run_command({"flag": broken}, "flag", "x", None) == FAILED


class _Interaction:
    def __init__(self, user: int) -> None:
        self.user = SimpleNamespace(id=user)
        self.said: list[str] = []
        self.deferred = False
        self.response = SimpleNamespace(send_message=self._send, defer=self._defer)
        self.followup = SimpleNamespace(send=self._send)

    async def _send(self, text: str, *, ephemeral: bool) -> None:
        assert ephemeral
        self.said.append(text)

    async def _defer(self, *, ephemeral: bool, thinking: bool) -> None:
        assert ephemeral
        assert thinking
        self.deferred = True


async def test_only_the_allowed_user_runs_a_command_and_the_answer_is_private() -> None:
    seen: list[tuple[str, str, str | None]] = []
    marks = _Marks(ALLOWED, _commands(seen))
    stranger, them = _Interaction(7), _Interaction(ALLOWED)
    await marks.answer(stranger, "flag", "x", None)  # type: ignore[arg-type]
    await marks.answer(them, "fav", "a" * 900, "m2")  # type: ignore[arg-type]
    assert stranger.said == [NOT_YOURS]
    assert them.deferred
    assert them.said == ["luna"]
    assert seen == [("fav", "a" * 500, "m2")]
