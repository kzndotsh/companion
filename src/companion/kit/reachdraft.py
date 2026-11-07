"""The last step every reach-out's draft goes through: record it as a would-send, or record why it
was dropped. The check itself is `core/reachout.py` `drafted`. A live send would go here too."""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.types import DecisionKind, Json
from companion.kit.record import Recorder


@dataclass(frozen=True, slots=True)
class DraftKeys:
    """How one kind of reach-out records a draft: its two decision keys, as they are stored; the
    kind a dropped one is recorded as; and what follows the key in a dropped one's reason."""

    dropped: str
    would: str
    dropped_kind: DecisionKind = DecisionKind.POLICY
    label: str = ""


def record_draft(
    rec: Recorder,
    keys: DraftKeys,
    got: tuple[str, str | None],
    detail: dict[str, Json],
    would: str,
) -> None:
    """A checked draft (`drafted`: the text, or empty with why it was dropped) as a decision. A kept
    one is recorded under `keys.would` with the reason `would`; a dropped one under `keys.dropped`,
    so it is not drafted again."""
    text, why = got
    if text:
        rec.decide(keys.would, detail, reason=would, kind=DecisionKind.INITIATE)
    else:
        rec.decide(
            keys.dropped,
            detail,
            reason=f"{keys.dropped}{keys.label}: {why}",
            kind=keys.dropped_kind,
        )
