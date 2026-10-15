"""Narrow untyped JSON from the wire into known shapes. Anything unexpected becomes empty."""

from __future__ import annotations

from typing import cast

from companion.core.prompt.request import TalkerRequest


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in cast("dict[object, object]", value).items()}


def seq(value: object) -> list[object]:
    return list(cast("list[object]", value)) if isinstance(value, list) else []


def integer(value: object) -> int:
    return value if isinstance(value, int) else 0


def number(value: object) -> float:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0.0


def string(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def system_blocks(request: TalkerRequest) -> list[dict[str, object]]:
    """The persona, cached, then the memory card. The card changes from turn to turn, so it comes
    last and carries no breakpoint of its own."""
    blocks: list[dict[str, object]] = [
        {"type": "text", "text": request.prefix.system, "cache_control": {"type": "ephemeral"}}
    ]
    if request.card:
        blocks.append({"type": "text", "text": request.card})
    return blocks


def messages_with_breakpoint(request: TalkerRequest) -> list[dict[str, object]]:
    """Wire messages, with a cache breakpoint on the last message before the new user turn.

    Everything up to and including that message is byte-identical from turn to turn, so the
    provider can cache the whole growing history once it passes its minimum length.
    """
    out: list[dict[str, object]] = []
    breakpoint_at = len(request.messages) - 2
    for i, m in enumerate(request.messages):
        if i == breakpoint_at:
            block = {"type": "text", "text": m.content, "cache_control": {"type": "ephemeral"}}
            out.append({"role": m.role, "content": [block]})
        else:
            out.append({"role": m.role, "content": m.content})
    return out
