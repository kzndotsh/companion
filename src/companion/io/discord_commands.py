"""`/flag`, `/fav` and `/mode` as Discord's own slash commands, and Flag this and Favorite this on a
message's Apps menu. Typed as text, a command name another app also uses brings up that app's
command; registered, Discord shows these as the bot's. They run the same command handlers as the
text commands (`daemon.chat_commands`), answer only the allowed user, and answer privately: the
answer is never part of the chat."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import discord
from discord import app_commands

from companion.core.turn.ack import ReactAndReply, Reaction
from companion.io.surface import Commands

log = logging.getLogger("companion.discord")
NOTE_CHARS = 500  # a note on a mark is a line or two
NOT_YOURS = "these commands are only for the person this bot talks to"
FAILED = "that didn't work, try again in a bit"


def said(answer: str | Reaction | ReactAndReply) -> str:
    """A command's answer as the text of a private reply: a reaction becomes its emoji."""
    if isinstance(answer, Reaction):
        return answer.emoji
    if isinstance(answer, ReactAndReply):
        return f"{answer.reaction.emoji} {answer.text}"
    return answer or "done"


async def run_command(commands: Commands, name: str, note: str, message_id: str | None) -> str:
    """Run one command by name. A failure is logged and answered, never raised to discord.py."""
    try:
        return said(await commands[name](note, message_id))
    except Exception:
        log.exception("command /%s failed", name)
        return FAILED


@dataclass(frozen=True, slots=True)
class _Marks:
    """Who may use the commands, and what they run."""

    allowed: int
    commands: Commands

    async def answer(
        self, interaction: discord.Interaction, name: str, note: str, message_id: str | None
    ) -> None:
        if interaction.user.id != self.allowed:
            await interaction.response.send_message(NOT_YOURS, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)  # /flag may ask a judge
        reply = await run_command(self.commands, name, note[:NOTE_CHARS], message_id)
        await interaction.followup.send(reply, ephemeral=True)


@dataclass(frozen=True, slots=True)
class _Menu:
    """A mark on a message's Apps menu: the command it runs, its name there, the note's prompt."""

    command: str
    title: str
    label: str


class _Note(discord.ui.Modal):
    """The optional note for a mark made from a message's Apps menu."""

    def __init__(self, marks: _Marks, menu: _Menu, message_id: str) -> None:
        super().__init__(title=menu.title)
        self.note: discord.ui.TextInput[_Note] = discord.ui.TextInput(
            label=menu.label,
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=NOTE_CHARS,
        )
        self.add_item(self.note)
        self._marks, self._command, self._id = marks, menu.command, message_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._marks.answer(interaction, self._command, self.note.value, self._id)


def command_tree(
    client: discord.Client, allowed: int, commands: Commands
) -> app_commands.CommandTree:
    """The commands, usable in a DM with the bot, whether it was added to a server or to an
    account. Discord learns of them when the tree is synced after login."""
    tree = app_commands.CommandTree(client)
    marks = _Marks(allowed, commands)
    where = app_commands.AppCommandContext(guild=False, dm_channel=True, private_channel=False)
    installs = app_commands.AppInstallationType(guild=True, user=True)

    def mark(name: str, description: str) -> app_commands.Command[Any, ..., None]:
        @app_commands.describe(note="what about it, in a few words (optional)")
        async def run(interaction: discord.Interaction, note: str = "") -> None:
            await marks.answer(interaction, name, note, None)

        return app_commands.Command(
            name=name,
            description=description,
            callback=run,
            allowed_contexts=where,
            allowed_installs=installs,
        )

    async def mode(interaction: discord.Interaction) -> None:
        await marks.answer(interaction, "mode", "", None)

    def on_message(menu: _Menu) -> app_commands.ContextMenu:
        async def run(interaction: discord.Interaction, message: discord.Message) -> None:
            if interaction.user.id != allowed:
                await interaction.response.send_message(NOT_YOURS, ephemeral=True)
                return
            await interaction.response.send_modal(_Note(marks, menu, str(message.id)))

        return app_commands.ContextMenu(
            name=menu.title, callback=run, allowed_contexts=where, allowed_installs=installs
        )

    tree.add_command(mark("flag", "Mark the last reply as off"))
    tree.add_command(mark("fav", "Mark the last reply as one you loved"))
    tree.add_command(
        app_commands.Command(
            name="mode",
            description="Which model is talking now",
            callback=mode,
            allowed_contexts=where,
            allowed_installs=installs,
        )
    )
    tree.add_command(on_message(_Menu("flag", "Flag this", "What feels off? (optional)")))
    tree.add_command(on_message(_Menu("fav", "Favorite this", "What did you love? (optional)")))
    return tree


async def sync(tree: app_commands.CommandTree) -> None:
    """Tell Discord the commands. On a failure the old ones stay; text commands still work."""
    try:
        synced = await tree.sync()
    except (discord.DiscordException, OSError) as err:
        status = getattr(err, "status", None)
        log.warning("discord: slash commands not synced (%s)", status or type(err).__name__)
        return
    log.info("discord: %d commands synced", len(synced))
