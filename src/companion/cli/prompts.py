"""`companion prompts`: the current version of every prompt, or the text of one."""

from __future__ import annotations

import argparse

from companion import prompts
from companion.kit.command import Command, Group, emit


def run(which: str | None = None) -> str:
    if which:
        name, _, version = which.partition("@")
        try:
            return prompts.get(name, version or None).text + "\n"
        except KeyError as err:
            return f"{err.args[0]}\n"
    rows = [
        (p.name, p.version, len(prompts.versions(p.name)), len(p.text.split()), p.sha)
        for p in prompts.current()
    ]
    width = max(len(r[0]) for r in rows)
    lines = [f"{'name'.ljust(width)}  version  of  words  hash"]
    lines += [f"{n.ljust(width)}  {v:7}  {c:2}  {w:5}  {s}" for n, v, c, w, s in rows]
    lines += ["", f"set hash {prompts.set_hash()}", "show one: companion prompts <name>[@version]"]
    return "\n".join(lines) + "\n"


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("which", nargs="?", help="a prompt name, optionally name@version")


COMMANDS = (
    Command(
        "prompts",
        Group.RUNNING,
        "the current version of every prompt, or the text of one",
        lambda a: emit(run(a.which)),
        _args,
    ),
)
