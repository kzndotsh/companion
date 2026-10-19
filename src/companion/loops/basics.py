"""Read their answer when the companion asked what to call them (J48)."""

from __future__ import annotations

import asyncio
import logging

from companion.core.basics import NAME_CAPTURE, NAME_SCHEMA, parse_name
from companion.core.extractor import Extractor
from companion.core.spend import purpose

TIMEOUT_SECONDS = 3.0
log = logging.getLogger("companion.basics")


async def judge_name(extractor: Extractor, asked: str, said: str) -> str | None:
    """The name they gave in reply, or None."""
    try:
        with purpose("basics"):
            result = await asyncio.wait_for(
                extractor.extract(
                    NAME_CAPTURE.text, f"COMPANION: {asked}\nUSER: {said}", NAME_SCHEMA
                ),
                TIMEOUT_SECONDS,
            )
    except Exception as err:
        log.warning("name capture failed or timed out: %r", err)
        return None
    return parse_name(result.data, said)
