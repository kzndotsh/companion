"""`companion` commands of the callbacks feature."""

from __future__ import annotations

from datetime import timedelta

from companion.core.clock import utc_now
from companion.features.audits.callbacks.logic import report
from companion.features.audits.callbacks.run import check_new
from companion.features.audits.callbacks.store import CallbackChecks
from companion.kit.services import Services


async def judge_now(x: Services, days: int, cap_usd: float) -> str:
    """Judge recent replies for callbacks, then report. For `companion audit callbacks`."""
    start = utc_now() - timedelta(days=days)
    judged, spent = await check_new(x.store, x.judge, x.rel, start, cap_usd)
    verdicts = x.store.part(CallbackChecks).since(x.rel, start)
    replies = {t: x.store.reply_text(x.rel, t) for t, c in verdicts if c.callback}
    shown = [(replies[t], c) for t, c in verdicts if c.callback][-8:]
    head = f"judged {judged} new replies for ${spent:.4f}\n"
    return head + report([c for _, c in verdicts], days, shown)
