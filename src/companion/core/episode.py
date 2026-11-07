"""When one episode of chat ends: after this long with no message. Episodes are cut here, a scene
ends with its episode, and their rhythm counts an episode's first message as a start."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from companion.core.types import Severity, UtteranceId

EPISODE_GAP = timedelta(hours=2)


@dataclass(frozen=True, slots=True)
class Episode:
    id: str
    first_id: UtteranceId
    last_id: UtteranceId
    start_at: datetime
    end_at: datetime
    messages: int
    kind: str
    scene_share: float
    top_severity: Severity
    firsts: tuple[str, ...]
    gist: str
    prompt: str
    at: datetime
