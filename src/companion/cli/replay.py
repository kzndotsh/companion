"""`companion replay <turn_id>`: rebuild what the fast loop saw, and say whether it matches."""

from __future__ import annotations

from pathlib import Path

from companion.core.replay import ReplayError
from companion.store.sqlite.replay import ReplayReport, replay_file


def render(report: ReplayReport) -> str:
    r = report.record
    lines = [
        f"turn {r.turn_id}  session {r.session_id}  model {r.model or '-'}",
        f"prefix {r.prefix_sha256[:12]}  request {r.request_sha256[:12]}  "
        + ("MATCH" if report.matched else "MISMATCH: the rebuilt request differs from the record"),
        "",
        "messages:",
    ]
    lines += [f"  [{m.role}] {m.content}" for m in report.request.messages]
    lines += ["", f"decisions ({len(report.decisions)}):"]
    lines += [f"  {d.kind}  {d.reason}" for d in report.decisions]
    return "\n".join(lines) + "\n"


def run(db: Path, turn_id: str) -> tuple[str, int]:
    try:
        report = replay_file(db, turn_id)
    except ReplayError as err:
        return f"{err}\n", 2
    return render(report), 0 if report.matched else 1
