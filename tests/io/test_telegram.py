from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

from companion.core.ack import ReactAndReply, Reaction
from companion.io.telegram import Telegram

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
