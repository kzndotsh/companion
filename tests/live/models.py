"""The judge model the live suites run on: Haiku, as the bot runs, unless COMPANION_LIVE_JUDGE_MODEL
names another, so one suite can be compared across models."""

from __future__ import annotations

import os

JUDGE_MODEL = os.environ.get("COMPANION_LIVE_JUDGE_MODEL", "anthropic/claude-haiku-5.5")
