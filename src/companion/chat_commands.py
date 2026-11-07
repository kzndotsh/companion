"""The commands they can send in the chat: `/flag` and `/fav` (typed `!flag` and `!fav` on Discord)
mark a reply and answer with a reaction, `/mode` says which talker answers."""

from __future__ import annotations

import logging

from companion.core import switch as sw
from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.flags import parse_flag
from companion.core.turn.reply import ReactAndReply, Reaction
from companion.core.types import (
    Favorite,
    FavoriteId,
    Flag,
    FlagId,
    RelationshipId,
    TurnId,
)
from companion.io.delivery import FAV, FAVORITE, FLAG, MODE, Commands
from companion.kit import curate
from companion.kit.record import new_id
from companion.memory.views import views_implicated
from companion.settings import Settings
from companion.store.sqlite.store import Store
from companion.turn.mode import mode_report

FLAG_REACTION = "✍"
FAVORITE_REACTION = "❤"
UNKNOWN_REPLY = (
    "can't tell which reply that was (it's from before i kept track), so nothing was marked."
    " send it again without replying, with a note saying which one"
)


def chat_commands(
    store: Store, rel: RelationshipId, judges: StructuredModel, s: Settings
) -> Commands:
    """The commands: `/flag` and `/fav` (typed `!flag` and `!fav` on Discord) answer with a
    reaction, `/mode` with which talker. `/flag` and `/fav` mark the latest reply, or, sent as a
    reply to one of its messages or of theirs, that turn, with any words after them as the
    comment."""

    def marked(replied_to: str | None) -> TurnId | None:
        if replied_to is None:
            return store.latest_turn(rel)
        return store.turn_of_message(rel, s.value(sw.PLATFORM), replied_to)

    async def flag(arg: str, replied_to: str | None) -> str | Reaction | ReactAndReply:
        turn = marked(replied_to)
        if turn is None:
            return UNKNOWN_REPLY if replied_to is not None else "nothing to flag yet"
        kind, comment = parse_flag(arg)
        store.add_flag(Flag(FlagId(new_id()), rel, turn, kind, comment, utc_now()))
        logging.getLogger("companion").info("flag on turn %s (%s): %s", turn[:8], kind, comment)
        implicated = await views_implicated(store, judges, rel, turn, comment)
        logging.getLogger("companion").debug("flag implicates %d view(s)", len(implicated))
        for claim in curate.retire_implicated_views(store, implicated):
            logging.getLogger("companion").info("flag retired a view: %s", claim)
        return Reaction(FLAG_REACTION)

    async def favorite(arg: str, replied_to: str | None) -> str | Reaction | ReactAndReply:
        turn = marked(replied_to)
        if turn is None:
            return UNKNOWN_REPLY if replied_to is not None else "nothing to favorite yet"
        store.add_favorite(Favorite(FavoriteId(new_id()), rel, turn, arg.strip(), utc_now()))
        logging.getLogger("companion").info("favorite on turn %s: %s", turn[:8], arg.strip())
        return Reaction(FAVORITE_REACTION)

    async def mode(arg: str, replied_to: str | None) -> str | Reaction | ReactAndReply:
        del arg, replied_to
        return mode_report(store, rel, utc_now(), s.everyday_model, s.scene_model)

    return {FLAG: flag, FAV: favorite, FAVORITE: favorite, MODE: mode}
