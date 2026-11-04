"""When one episode of chat ends: after this long with no message. Episodes are cut here, a scene
ends with its episode, and their rhythm counts an episode's first message as a start."""

from __future__ import annotations

from datetime import timedelta

EPISODE_GAP = timedelta(hours=2)
