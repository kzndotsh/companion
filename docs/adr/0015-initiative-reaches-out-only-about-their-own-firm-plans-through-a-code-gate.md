# 0015. Initiative reaches out only about their own firm plans, through a code gate, shadow first

**Status:** accepted 2026-10-18; what can be reached out about and the back-off counts are replaced
by ADR 0021 (2026-10-25). Originally recording what was built on 2026-10-17 and 2026-10-18 (card A1 of the
audit synthesis). Still shadow mode only: nothing is sent.

**Context.** The audits found no project that closes the loop on a reach-out. The common failures were
about order and state, not code: paying before checking, a bot's own message resetting the clock,
counters lost on restart. The proactive-messaging review (2026-10-18) found that users dislike a bot
reacting to their silence, interrupting, writing from nowhere and having no off switch. They like one
specific question about one thing they mentioned, at an expected time.

**Decision.** The companion may message first only about something they said about their own near
future, and code decides whether and when.

- **What can be reached out about.** An open loop: a plan, appointment, deadline or occasion from a
  USER message said for real, with the exact quote (ADR 0001). A small model labels it (when, scale,
  sensitivity, certainty, whether it is about the companion, and its kind). Code keeps only firm plans
  about their own life and never records a sensitive one (2 or 3), so a sensitive loop can never be
  raised. Nothing is triggered by their silence, their mood or a timer alone.
- **When.** The kind sets the time (`core/openloops.py`, now `features/openloops/logic.py`):
  - follow-up: the morning after it happens;
  - celebrate: the day itself, mid-morning;
  - encourage: early that morning, just after quiet hours.

  A celebration or encouragement expires at the end of its day. A follow-up keeps two days. A loop they
  settle themselves ("it went fine") is closed as resolved and never asked about.
- **The gate.** A pure function (`core/initiative.py`, now `features/openloops/gate.py`) checks, in order: quiet hours (11 PM to 8 AM,
  their zone), a scene in progress, one reach-out a day, at least 20 hours since the last, a back-off
  after an unanswered live reach-out (72 hours; after two in a row it waits for them to write first),
  and an active chat (90 minutes). The first that holds is the reason. A hold never drops a loop; it
  waits for the next tick.
- **Paid calls come last.** The draft is the only model call at send time, made only after every cheap
  gate passed (a test enforces it). It is one short message about the one thing, by kind (ask how it
  went, wish them well, cheer them on), never saying it remembered or tracked it.
- **Everything is logged.** Every hold (once per loop and reason), expiry, closure and would-send is a
  decision with a reason written by code (ADR 0003, 0006). Loops, their events and reach-outs are
  append-only tables (ADR 0002).
- **Shadow first.** `COMPANION_INITIATIVE` defaults to shadow: the tick runs every 15 minutes, drafts,
  records "would send" and sends nothing. Shadow drafts never count toward the back-off. `off` disables
  it. Read it with `uv run companion initiative`.

**Why.** Labels and kinds checked by code replaced prompt rules. In shadow mode the first extractor
recorded "maybe someday" statements and things about the bot itself, and scheduled a birthday for the
morning after.

**Before it may send for real.**
- The owner marks shadow drafts as wanted or not, and about five on real plans read well and land at
  sensible times.
- The outcome of each live reach-out is recorded (card A6: seen, replied, a "stop" signal).
- A live send is charged against the spend cap before the transport call.
- The time zone is a named zone, not the machine's current offset, so winter times land right.

**Consequences.**
- A loop extracted by an older prompt can be dropped by hand with a reason; nothing is deleted.
- The tick is its own loop beside the slow loop, not inside it.
- Going live is a settings change plus these conditions, not new code.
- A mood never triggers a reach-out (ADR 0016).

**Since:** the extractor is `system/openloops` v3 and the draft prompt `system/openloops-draft` v2. The
gate, caps and conditions above are unchanged. Initiative is still shadow only.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) Reaching out on silence, mood or a timer alone. A model deciding when to speak. Drafting
before the cheap gates.

**Reverses if.** Real outcomes show reach-outs unwelcome even when the gate passes, or a scored "should
I speak now" judge beats the rules on marked drafts.
