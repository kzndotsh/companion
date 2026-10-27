from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import discord
from discord import app_commands

from companion.core.turn.ack import ReactAndReply, Reaction
from companion.io.discord_commands import (
    FAILED,
    NOT_YOURS,
    _Marks,  # pyright: ignore[reportPrivateUsage]
    command_tree,
    run_command,
    said,
)
from companion.io.surface import Commands

ALLOWED = 42


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
