"""Fixtures: a recorded turn, what the right reply looks like, and how to check it.

A fixture names a turn in the local ledger instead of copying its text. The conversation stays in
the database, and a fixture file holds only an opaque id, a generic description and the checks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from companion.core.types import Json


class FixtureError(ValueError):
    """A fixture file is malformed."""


@dataclass(frozen=True, slots=True)
class MaxWords:
    n: int


@dataclass(frozen=True, slots=True)
class Regex:
    """`must_match` False means the reply fails if the pattern appears."""

    pattern: str
    must_match: bool = False
    ignore_case: bool = True


@dataclass(frozen=True, slots=True)
class JudgeCheck:
    criterion: str


type Check = MaxWords | Regex | JudgeCheck


@dataclass(frozen=True, slots=True)
class Fixture:
    id: str
    description: str
    turn: str
    checks: tuple[Check, ...]


def _obj(value: Json) -> dict[str, Json]:
    if not isinstance(value, dict):
        msg = "expected an object"
        raise FixtureError(msg)
    return cast("dict[str, Json]", value)


def _text(d: dict[str, Json], key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        msg = f"{key!r} must be a non-empty string"
        raise FixtureError(msg)
    return v


def _check(raw: Json) -> Check:
    d = _obj(raw)
    kind = d.get("kind")
    if kind == "max_words":
        n = d.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            msg = "max_words needs a positive integer n"
            raise FixtureError(msg)
        return MaxWords(n)
    if kind in ("regex", "not_regex"):
        pattern = _text(d, "pattern")
        try:
            re.compile(pattern)
        except re.error as err:
            msg = f"bad pattern {pattern!r}: {err}"
            raise FixtureError(msg) from err
        return Regex(
            pattern, must_match=kind == "regex", ignore_case=d.get("ignore_case") is not False
        )
    if kind == "judge":
        return JudgeCheck(_text(d, "criterion"))
    msg = f"unknown check kind {kind!r}"
    raise FixtureError(msg)


def parse_fixture(raw: Json) -> Fixture:
    d = _obj(raw)
    checks = d.get("checks")
    if not isinstance(checks, list) or not checks:
        msg = "a fixture needs at least one check"
        raise FixtureError(msg)
    return Fixture(
        id=_text(d, "id"),
        description=_text(d, "description"),
        turn=_text(d, "turn"),
        checks=tuple(_check(c) for c in cast("list[Json]", checks)),
    )


def load_fixtures(directory: Path) -> list[Fixture]:
    found: list[Fixture] = []
    for path in sorted(directory.glob("*.json")):
        try:
            found.append(parse_fixture(json.loads(path.read_text(encoding="utf-8"))))
        except (FixtureError, json.JSONDecodeError) as err:
            msg = f"{path.name}: {err}"
            raise FixtureError(msg) from err
    ids = [f.id for f in found]
    if len(ids) != len(set(ids)):
        msg = "fixture ids must be unique"
        raise FixtureError(msg)
    return found
