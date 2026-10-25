"""What `/mode` answers: which talker wrote the last reply and why, and whether a pretend scene is
under way now, so the mode can be seen without a flag. A command's answer is never stored, so the
model never sees it."""

from __future__ import annotations

from datetime import datetime

from companion.core.frames import scene_frame
from companion.core.history import HISTORY_LIMIT
from companion.core.types import Frame, RelationshipId
from companion.store.sqlite.store import Store
from companion.turn.route import routed_to_roleplay


def mode_report(
    store: Store, rel: RelationshipId, now: datetime, everyday: str, roleplay: str
) -> str:
    """Two lines: the last reply's talker with the reason code logged, and the scene now."""
    turn = store.latest_turn(rel)
    if turn is None:
        return "no replies yet"
    routes = [d for d in store.decisions_for_turn(rel, turn) if d.has_key("route")]
    if routes and routed_to_roleplay(routes[-1]):
        why = routes[-1].reason.partition(": ")[2] or "routed there"
        last = f"last reply: the roleplay talker ({roleplay}), because {why}"
    else:
        last = f"last reply: the everyday talker ({everyday})"
    frame = scene_frame(store.history_before(rel, now, HISTORY_LIMIT), now)
    if frame is not Frame.REAL:
        scene = (
            "now: a pretend scene is under way, so your next message goes to the roleplay talker"
        )
    elif routes and routed_to_roleplay(routes[-1]):
        scene = "now: no scene; intimate talk stays with the roleplay talker while it carries on"
    else:
        scene = "now: no scene; your next message goes to the everyday talker unless it starts one"
    return f"{last}\n{scene}"
