"""Operator content guidelines (ADR 0017): what a deployment allows, chosen by whoever runs it.

A guidelines file has a short settings block between `+++` lines, then plain text. The settings say
what code does (today only `route_intimate`: whether intimate talk may go to the scene talker). The
text, if any, is added to the talker's system prompt under its own heading. The floor in
`core/floor.py` is not a setting and no file changes it.

Public files are versioned prompts at `prompts/guidelines/<id>/vN.md` (ADR 0013); private ones live
at `data/guidelines/<id>.md`, are never committed, and win over a public one of the same id.
`COMPANION_GUIDELINES=<id>` picks one; unset means `default`, which routes nothing.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from companion import prompts

GUIDELINES_ENV = "COMPANION_GUIDELINES"
PRIVATE_DIR = Path("data/guidelines")
DEFAULT = "default"
HEADING = "## Operator guidelines"
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
_BLOCK = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n?(.*)\Z", re.DOTALL)


class GuidelinesError(ValueError):
    """Guidelines that cannot be loaded, with the reason in plain words."""


@dataclass(frozen=True, slots=True)
class Guidelines:
    id: str
    version: str  # "vN" for a public file, "local" for a private one
    route_intimate: bool
    text: str

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def parse(raw: str, gid: str, version: str) -> Guidelines:
    m = _BLOCK.match(raw)
    if m is None:
        msg = f"guidelines {gid!r} must start with a settings block between +++ lines"
        raise GuidelinesError(msg)
    try:
        settings = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as err:
        msg = f"guidelines {gid!r} have unreadable settings: {err}"
        raise GuidelinesError(msg) from err
    unknown = set(settings) - {"route_intimate"}
    route = settings.get("route_intimate", False)
    if unknown or not isinstance(route, bool):
        msg = f"guidelines {gid!r}: the only setting is route_intimate = true or false"
        raise GuidelinesError(msg)
    return Guidelines(gid, version, route, m.group(2).strip())


def load(gid: str, private_dir: Path = PRIVATE_DIR) -> Guidelines:
    """The private file if there is one, otherwise the current public version."""
    if not _ID.fullmatch(gid):
        msg = f"guidelines id {gid!r} must be lowercase letters, digits and dashes"
        raise GuidelinesError(msg)
    private = private_dir / f"{gid}.md"
    if private.is_file():
        return parse(private.read_text(encoding="utf-8"), gid, "local")
    try:
        prompt = prompts.get(f"guidelines/{gid}")
    except KeyError as err:
        msg = f"no guidelines {gid!r}: not in {private_dir} and not in prompts/guidelines"
        raise GuidelinesError(msg) from err
    return parse(prompt.raw, gid, prompt.version)


def chosen(private_dir: Path = PRIVATE_DIR) -> Guidelines:
    """The guidelines `COMPANION_GUIDELINES` names, or the default."""
    return load(os.environ.get(GUIDELINES_ENV, "").strip() or DEFAULT, private_dir)


def with_guidelines(system: str, guidelines: Guidelines) -> str:
    """The system prompt with the operator's text under its heading, or unchanged without text."""
    if not guidelines.text:
        return system
    return f"{system.rstrip()}\n\n{HEADING}\n\n{guidelines.text}\n"
