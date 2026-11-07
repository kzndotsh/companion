"""`companion replay <turn_id>`: rebuild what the reply path saw, and say whether it matches."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from companion.core.replay import ReplayError
from companion.kit.command import Command, Group, db_args
from companion.kit.target import resolve_db
from companion.store.sqlite.replay import ReplayReport, replay_file


def _prompt_in_order(report: ReplayReport) -> list[str]:
    """What the talker was sent, in the order it read it: the persona, the card, the messages."""
    request = report.request
    words = len(request.prefix.system.split())
    lines = [
        f"system block 1, the persona ({words} words, cached):",
        request.prefix.system,
        "",
    ]
    if request.card:
        lines += ["system block 2, the card (clock, memory, notes):", request.card, ""]
    lines += [f"messages ({len(request.messages)}):"]
    lines += [f"  [{m.role}] {m.content}" for m in request.messages]
    if request.tail:
        lines += ["", "after the history (system):", request.tail]
    return lines


def render(report: ReplayReport, *, show_prompt: bool = False) -> str:
    r = report.record
    lines = [
        f"turn {r.turn_id}  model {r.model or '-'}",
        f"prefix {r.prefix_sha256[:12]}  request {r.request_sha256[:12]}  "
        + ("MATCH" if report.matched else "MISMATCH: the rebuilt request differs from the record"),
        "",
    ]
    if show_prompt:
        lines += _prompt_in_order(report)
    else:
        lines += ["messages:"]
        lines += [f"  [{m.role}] {m.content}" for m in report.request.messages]
        if report.request.card:
            lines += ["", "memory card (system block):", report.request.card]
        if report.request.tail:
            lines += ["", "after the history (system):", report.request.tail]
    lines += ["", f"decisions ({len(report.decisions)}):"]
    lines += [f"  {d.kind}  {d.reason}" for d in report.decisions]
    return "\n".join(lines) + "\n"


def run(db: Path, turn_id: str, *, show_prompt: bool = False) -> tuple[str, int]:
    try:
        report = replay_file(db, turn_id)
    except ReplayError as err:
        return f"{err}\n", 2
    return render(report, show_prompt=show_prompt), 0 if report.matched else 1


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument("turn_id")
    p.add_argument(
        "--show-prompt",
        action="store_true",
        help="print everything the talker was sent, in order, with the persona in full",
    )
    db_args(p, relationship=False)


def _run(a: argparse.Namespace) -> int:
    out, code = run(resolve_db(a.db), str(a.turn_id), show_prompt=bool(a.show_prompt))
    (sys.stdout if code != 2 else sys.stderr).write(out)
    return code


COMMANDS = (
    Command("replay", Group.FLAGS, "rebuild what the reply path saw for one turn", _run, _args),
)
