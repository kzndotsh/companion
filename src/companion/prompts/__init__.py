"""Every prompt the bot sends, as versioned text files.

A prompt is a name and a version: `system/ack/v1.md`. The manifest says which version is current.
A shipped version is never edited; a change is a new file with an entry in `CHANGELOG.md`, so what
changed is visible and a bad change is one line to undo. Each judgement and decision that uses a
prompt logs `name@version`. Some prompts hold placeholders written `$name`, which code fills in
with `render`.

The folders say what a prompt is. `system/` holds the system prompts, `notes/` the lines added to
the talker's system block each turn, `messages/` text sent to the user.

`COMPANION_PROMPT_OVERRIDES="system/ack=v2,notes/length=v3"` picks other versions for an
experiment. It is read when a prompt is first loaded, so set it before the process starts.
"""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from string import Template

OVERRIDES_ENV = "COMPANION_PROMPT_OVERRIDES"
_VERSION = re.compile(r"v(\d+)\.md")


@dataclass(frozen=True, slots=True)
class Prompt:
    name: str
    version: str
    raw: str  # exactly the file, with its closing newline

    @property
    def text(self) -> str:
        """The prompt without the file's closing newline, which is how it reads in code."""
        return self.raw.removesuffix("\n")

    @property
    def ref(self) -> str:
        """`name@version`, what a decision logs."""
        return f"{self.name}@{self.version}"

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.raw.encode()).hexdigest()[:12]

    def render(self, **values: object) -> str:
        """The text with each `$name` filled in. A missing value is an error, never a blank."""
        return Template(self.text).substitute({k: str(v) for k, v in values.items()})

    @property
    def placeholders(self) -> frozenset[str]:
        return frozenset(Template(self.text).get_identifiers())


def _root() -> Traversable:
    return resources.files(__package__)


def manifest() -> dict[str, str]:
    """The current version of every prompt, with any experiment overrides applied."""
    current = tomllib.loads(_root().joinpath("manifest.toml").read_text(encoding="utf-8"))
    out = {name: str(version) for name, version in current.items()}
    for item in filter(None, os.environ.get(OVERRIDES_ENV, "").split(",")):
        name, _, version = item.partition("=")
        if name.strip() not in out:
            msg = f"{OVERRIDES_ENV} names an unknown prompt {name.strip()!r}"
            raise KeyError(msg)
        out[name.strip()] = version.strip()
    return out


def versions(name: str) -> list[str]:
    """Every version file that exists for a prompt, oldest first."""
    folder = _root().joinpath(*name.split("/"))
    found = sorted(
        (int(m.group(1)), m.group(0)[:-3])
        for f in folder.iterdir()
        if (m := _VERSION.fullmatch(f.name))
    )
    return [version for _, version in found]


def get(name: str, version: str | None = None) -> Prompt:
    """The current version of a prompt, or the one asked for."""
    chosen = version or manifest().get(name)
    if chosen is None:
        msg = f"no prompt named {name!r}"
        raise KeyError(msg)
    path = _root().joinpath(*name.split("/"), f"{chosen}.md")
    if not path.is_file():
        msg = f"prompt {name!r} has no version {chosen!r}"
        raise KeyError(msg)
    return Prompt(name, chosen, path.read_text(encoding="utf-8"))


def current() -> list[Prompt]:
    return [get(name) for name in sorted(manifest())]


def set_hash() -> str:
    """One short hash of every current prompt, for the startup line."""
    joined = "\n".join(f"{p.ref}:{p.sha}" for p in current())
    return hashlib.sha256(joined.encode()).hexdigest()[:8]
