"""Prompts kept as versioned text files: `<folder>/<name>/vN.md`, with a `manifest.toml` that says
which version of each is current. A shipped version is never edited; a change is a new file. A
prompt may hold placeholders written `$name`, filled in with `render`. An environment variable
(`name=version,...`) can pick other versions for an experiment; it is read on every lookup.
"""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from string import Template

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


@dataclass(frozen=True, slots=True)
class Library:
    """A folder of versioned prompts and the environment variable that overrides its versions."""

    root: Traversable
    overrides_env: str

    def manifest(self) -> dict[str, str]:
        """The current version of every prompt, with any experiment overrides applied."""
        text = self.root.joinpath("manifest.toml").read_text(encoding="utf-8")
        out = {name: str(version) for name, version in tomllib.loads(text).items()}
        for item in filter(None, os.environ.get(self.overrides_env, "").split(",")):
            name, _, version = item.partition("=")
            if name.strip() not in out:
                msg = f"{self.overrides_env} names an unknown prompt {name.strip()!r}"
                raise KeyError(msg)
            out[name.strip()] = version.strip()
        return out

    def versions(self, name: str) -> list[str]:
        """Every version file that exists for a prompt, oldest first."""
        folder = self.root.joinpath(*name.split("/"))
        found = sorted(
            (int(m.group(1)), m.group(0)[:-3])
            for f in folder.iterdir()
            if (m := _VERSION.fullmatch(f.name))
        )
        return [version for _, version in found]

    def get(self, name: str, version: str | None = None) -> Prompt:
        """The current version of a prompt, or the one asked for."""
        chosen = version or self.manifest().get(name)
        if chosen is None:
            msg = f"no prompt named {name!r}"
            raise KeyError(msg)
        path = self.root.joinpath(*name.split("/"), f"{chosen}.md")
        if not path.is_file():
            msg = f"prompt {name!r} has no version {chosen!r}"
            raise KeyError(msg)
        return Prompt(name, chosen, path.read_text(encoding="utf-8"))

    def current(self) -> list[Prompt]:
        return [self.get(name) for name in sorted(self.manifest())]

    def set_hash(self) -> str:
        """One short hash of every current prompt, for a startup line."""
        joined = "\n".join(f"{p.ref}:{p.sha}" for p in self.current())
        return hashlib.sha256(joined.encode()).hexdigest()[:8]
