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


@dataclass(frozen=True, slots=True)
class EmpathyCheck:
    """Scored 0 to 2 on reaction, interpretation and exploration (the EPITOME parts). Passes with
    a reaction and at least one of the other two."""


type Check = MaxWords | Regex | JudgeCheck | EmpathyCheck


@dataclass(frozen=True, slots=True)
class Script:
    """A conversation written in the fixture, so it needs no database and anyone can rerun it."""

    history: tuple[tuple[str, str], ...]  # (role, text), role is "user" or "assistant"
    user: str
    memory: str = ""  # an optional memory block, rendered like the real one
    clock: str = ""  # an optional line like "Right now it is Friday 02:15."
    labels: tuple[int, str, bool, bool, bool] | None = (
        None  # severity, stance, vague, medical, rude
    )
    lore: tuple[str, ...] = ()  # its own tastes, as the lore look-up would find them (ADR 0020)


@dataclass(frozen=True, slots=True)
class Fixture:
    """Either a recorded turn in the local database, or a script. Never both."""

    id: str
    description: str
    checks: tuple[Check, ...]
    turn: str | None = None
    script: Script | None = None
    labels: tuple[int, str, bool, bool, bool] | None = None  # for a recorded turn, as a script has


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
    if kind == "epitome":
        return EmpathyCheck()
    msg = f"unknown check kind {kind!r}"
    raise FixtureError(msg)


def _labels(raw: Json) -> tuple[int, str, bool, bool, bool] | None:
    if raw is None:
        return None
    d = _obj(raw)
    severity, stance, vague = d.get("severity"), d.get("stance"), d.get("vague")
    if isinstance(severity, bool) or not isinstance(severity, int) or not isinstance(stance, str):
        msg = "script.labels needs an integer severity and a text stance"
        raise FixtureError(msg)
    return severity, stance, bool(vague), bool(d.get("medical")), bool(d.get("rude"))


def _script(raw: Json) -> Script:
    d = _obj(raw)
    history = d.get("history", [])
    if not isinstance(history, list):
        msg = "script.history must be a list"
        raise FixtureError(msg)
    turns: list[tuple[str, str]] = []
    for item in cast("list[Json]", history):
        t = _obj(item)
        role = _text(t, "role")
        if role not in ("user", "assistant"):
            msg = f"unknown role {role!r}"
            raise FixtureError(msg)
        turns.append((role, _text(t, "text")))
    memory = d.get("memory", "")
    if not isinstance(memory, str):
        msg = "script.memory must be text"
        raise FixtureError(msg)
    clock = d.get("clock", "")
    if not isinstance(clock, str):
        msg = "script.clock must be text"
        raise FixtureError(msg)
    lore = d.get("lore", [])
    if not isinstance(lore, list) or not all(isinstance(x, str) for x in lore):
        msg = "script.lore must be a list of text"
        raise FixtureError(msg)
    return Script(
        tuple(turns),
        _text(d, "user"),
        memory,
        clock,
        _labels(d.get("labels")),
        lore=tuple(str(x) for x in cast("list[Json]", lore)),
    )


def parse_fixture(raw: Json) -> Fixture:
    d = _obj(raw)
    checks = d.get("checks")
    if not isinstance(checks, list) or not checks:
        msg = "a fixture needs at least one check"
        raise FixtureError(msg)
    turn, script = d.get("turn"), d.get("script")
    if (turn is None) == (script is None):
        msg = "a fixture needs exactly one of turn and script"
        raise FixtureError(msg)
    return Fixture(
        id=_text(d, "id"),
        description=_text(d, "description"),
        checks=tuple(_check(c) for c in cast("list[Json]", checks)),
        turn=_text(d, "turn") if turn is not None else None,
        script=_script(script) if script is not None else None,
        labels=_labels(d.get("labels")),
    )


def load_fixtures(*directories: Path) -> list[Fixture]:
    """Every fixture in the given directories. A directory that does not exist is skipped."""
    found: list[Fixture] = []
    for path in sorted(p for d in directories for p in d.glob("*.json")):
        try:
            fixture = parse_fixture(json.loads(path.read_text(encoding="utf-8")))
        except (FixtureError, json.JSONDecodeError) as err:
            msg = f"{path.name}: {err}"
            raise FixtureError(msg) from err
        if (
            fixture.id != path.stem
        ):  # `--fixture NAME` matches the id; a different file name hides it
            msg = f"{path.name}: its id is {fixture.id!r}; the file must be named {fixture.id}.json"
            raise FixtureError(msg)
        found.append(fixture)
    ids = [f.id for f in found]
    if len(ids) != len(set(ids)):
        msg = "fixture ids must be unique"
        raise FixtureError(msg)
    return found
