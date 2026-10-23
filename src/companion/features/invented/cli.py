"""`companion` commands of the invented feature."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from companion.core.clock import utc_now
from companion.features.invented.logic import report as invented_report
from companion.features.invented.run import check_new as check_invented
from companion.loops.services import Services


async def judge_now(x: Services, days: int, cap_usd: float, dump: Path | None = None) -> str:
    """Judge recent replies for made-up facts about the user, then report (G42)."""
    start = utc_now() - timedelta(days=days)
    judged, spent = await check_invented(x.store, x.judge, x.rel, start, cap_usd)
    checks = x.store.invented_since(x.rel, start)
    if dump is not None:
        dump.write_text(
            json.dumps(x.store.invented_candidates(x.rel, start), ensure_ascii=False, indent=1)
        )
    return f"judged {judged} new replies for ${spent:.4f}\n" + invented_report(checks, days)
