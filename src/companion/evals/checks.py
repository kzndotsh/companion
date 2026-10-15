"""Checks that need no model. Cheap, exact and repeatable."""

from __future__ import annotations

import re
from typing import Literal

from companion.evals.fixtures import MaxWords, Regex

Verdict = Literal["pass", "fail", "unclear"]


def run_deterministic(check: MaxWords | Regex, reply: str) -> Verdict:
    if isinstance(check, MaxWords):
        return "pass" if len(reply.split()) <= check.n else "fail"
    flags = re.IGNORECASE if check.ignore_case else 0
    found = re.search(check.pattern, reply, flags | re.MULTILINE) is not None
    return "pass" if found == check.must_match else "fail"
