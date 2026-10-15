from __future__ import annotations

import json

import httpx

from companion.io.telegram import Telegram

ALLOWED = 42


def _update(text: str, user: int = ALLOWED) -> dict[str, object]:
    return {"update_id": 1, "message": {"text": text, "from": {"id": user}, "chat": {"id": 7}}}


async def _run(update: dict[str, object]) -> tuple[list[str], list[str]]:
    calls: list[str] = []
    sent: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        method = str(req.url).rsplit("/", 1)[-1]
        calls.append(method)
        if method == "sendMessage":
            sent.append(json.loads(req.content)["text"])
        return httpx.Response(200, json={"ok": True, "result": True})

    seen: list[str] = []

    async def talk(text: str) -> str:
        seen.append(text)
        return "reply"

    async def flag(arg: str) -> str:
        seen.append(f"FLAG:{arg}")
        return "noted"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await Telegram("t", ALLOWED, client).handle_update(update, talk, {"flag": flag})
    return seen, sent


async def test_plain_text_goes_to_the_model() -> None:
    seen, sent = await _run(_update("hello"))
    assert seen == ["hello"]
    assert sent == ["reply"]


async def test_flag_command_never_reaches_the_model() -> None:
    seen, sent = await _run(_update("/flag forgot you knew"))
    assert seen == ["FLAG:forgot you knew"]
    assert sent == ["noted"]


async def test_flag_with_bot_suffix_is_the_same_command() -> None:
    seen, _ = await _run(_update("/flag@my_bot too_much"))
    assert seen == ["FLAG:too_much"]


async def test_unknown_commands_and_start_are_ignored() -> None:
    for text in ("/start", "/nonsense"):
        seen, sent = await _run(_update(text))
        assert seen == []
        assert sent == []


async def test_other_users_are_ignored() -> None:
    seen, sent = await _run(_update("hello", user=999))
    assert seen == []
    assert sent == []
