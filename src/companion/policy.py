"""Operator content policy (ADR 0017): what a deployment allows, chosen by whoever runs it.

A policy file has a short settings block between `+++` lines, then plain text. The settings say
what code does (today only `route_intimate`: whether intimate talk may go to the scene talker). The
text, if any, is added to the talker's system prompt under its own heading. The floor in
`core/floor.py` is not a setting and no file changes it.

Public files are versioned prompts at `prompts/policy/<id>/vN.md` (ADR 0013); private ones live
at `data/policy/<id>.md`, are never committed, and win over a public one of the same id.
`COMPANION_POLICY=<id>` picks one; unset means `default`, which routes nothing.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from companion import prompts

POLICY_ENV = "COMPANION_POLICY"
PRIVATE_DIR = Path("data/policy")
DEFAULT = "default"
HEADING = "## Operator policy"
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
_BLOCK = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n?(.*)\Z", re.DOTALL)


class PolicyError(ValueError):
    """Policy that cannot be loaded, with the reason in plain words."""


@dataclass(frozen=True, slots=True)
class Policy:
    id: str
    version: str  # "vN" for a public file, "local" for a private one
    route_intimate: bool
    text: str

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def parse(raw: str, gid: str, version: str) -> Policy:
    m = _BLOCK.match(raw)
    if m is None:
        msg = f"policy {gid!r} must start with a settings block between +++ lines"
        raise PolicyError(msg)
    try:
        settings = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as err:
        msg = f"policy {gid!r} has unreadable settings: {err}"
        raise PolicyError(msg) from err
    unknown = set(settings) - {"route_intimate"}
    route = settings.get("route_intimate", False)
    if unknown or not isinstance(route, bool):
        msg = f"policy {gid!r}: the only setting is route_intimate = true or false"
        raise PolicyError(msg)
    return Policy(gid, version, route, m.group(2).strip())


def load(gid: str, private_dir: Path = PRIVATE_DIR) -> Policy:
    """The private file if there is one, otherwise the current public version."""
    if not _ID.fullmatch(gid):
        msg = f"policy id {gid!r} must be lowercase letters, digits and dashes"
        raise PolicyError(msg)
    private = private_dir / f"{gid}.md"
    if private.is_file():
        return parse(private.read_text(encoding="utf-8"), gid, "local")
    try:
        prompt = prompts.get(f"policy/{gid}")
    except KeyError as err:
        msg = f"no policy {gid!r}: not in {private_dir} and not in prompts/policy"
        raise PolicyError(msg) from err
    return parse(prompt.raw, gid, prompt.version)


def chosen(private_dir: Path = PRIVATE_DIR) -> Policy:
    """The policy `COMPANION_POLICY` names, or the default."""
    return load(os.environ.get(POLICY_ENV, "").strip() or DEFAULT, private_dir)


def with_policy(system: str, policy: Policy) -> str:
    """The system prompt with the operator's text under its heading, or unchanged without text."""
    if not policy.text:
        return system
    return f"{system.rstrip()}\n\n{HEADING}\n\n{policy.text}\n"
