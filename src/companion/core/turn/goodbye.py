"""Whether a message says they are leaving: a goodbye, a goodnight, "gotta run". A moment like that
is never casual, and nothing should read as a pull to stay."""

from __future__ import annotations

import re

LEAVING = re.compile(
    r"\b(?:bye+|goodbye|cya|see ya|ttyl|talk (?:to you )?later|gtg|g2g|gotta (?:go|run|head)"
    r"|got to go|have to go|heading (?:to bed|out|off)|(?:going|off) to (?:bed|sleep)|sleep well)\b"
    r"|(?:^|[,.!]\s*|\b(?:ok|okay|alright|well)\s+)(?:good ?night|night night|nite|night|gn)\b",
    re.IGNORECASE,
)


def leaving(text: str) -> bool:
    return LEAVING.search(text) is not None
