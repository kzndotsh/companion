"""Narrow untyped JSON from the wire into known shapes. Anything unexpected becomes empty."""

from __future__ import annotations

from typing import cast


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(k): v for k, v in cast("dict[object, object]", value).items()}


def seq(value: object) -> list[object]:
    return list(cast("list[object]", value)) if isinstance(value, list) else []


def integer(value: object) -> int:
    return value if isinstance(value, int) else 0


def string(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default
