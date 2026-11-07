# Threads (ADR 0023; plans: J15, ADR 0015)

A thread is one thing the companion may bring up on its own: what it is, where it came from (`Source`), when
it fits, how sensitive it is, and a state (open, asked, resolved, expired, dropped) kept as an event log.
Every source writes threads; the note and the reach-out read them. Today there is one source, plans, so the
rest of this page is about plans. The interrupted story, weekly rhythms, milestones and pending outcomes, and
a topic gone quiet join as sources (ADR 0023, card R21). The tables keep their first names (`open_loops`,
`open_loop_events`, `reach_outs`), and decision keys and prompts are unchanged, so
history reads the same.

**Plans.** Things they said about their own near future that a friend would ask about later, such as a plan, an appointment or something they are waiting on. It brings one up when they next write, and in shadow it works out when it would reach out first.

**Status:** the note when they write is live. Reaching out is shadow (review by 2026-11-24, given more time at its review of 2026-11-03, judged on would-sends that read right to the owner, none in quiet hours or mid-chat). Switch: `COMPANION_INITIATIVE` (`shadow` default, `off`), which stops only the 15-minute tick. Reading plans (in the memory pass's batch, after a memory pass) and the note (before the reply) run whatever it says.

## How it works

**Reading plans.** The open-loop pass runs inside the memory pass's batch, after the beliefs, with one small-model call per batch (`system/openloops`, purpose `loops`). It has its own bookmark (`open_loop_runs`), so it never depends on the belief pass. It reads up to 40 messages per batch, with 4 messages of earlier context, and up to 3 batches per pass. The model only labels: the quote, a short claim, when it happens as they said it, a scale (`minutes`, `hours`, `days`, `unknown`), a sensitivity from 0 to 3, a certainty (`firm`, `maybe`, `wish`), whether it is about the companion, and a kind. Code decides what to keep. A candidate is dropped, with the reason logged, when (checked in this order, so a sensitive one is always logged as sensitive):

- sensitivity is 2 or more, so a sensitive plan is never raised on its own
- the cited message is not found, or no single message of theirs holds the quote
- it was not said by them for real (a scene or the companion's own words)
- the quote is not word for word in their message
- the scale is `minutes`, or it is about the companion or the chat
- the certainty is `wish`, or `maybe` while `COMPANION_HEDGED_PLANS=off` (strict), or the kind is unknown
- a celebration or encouragement has no day after today to land on
- the claim is empty or over 160 characters
- the follow-up time was already more than 3 days past
- the reader marks it as the same thing as a waiting loop of the same kind (`same_as`, `L1`) or as an earlier item in its own answer (`N1`), logged as `open loop rejected: the same thing as ...`; a different kind is kept, so a birthday marked on the day and asked about after stay two (`repeats`, `system/openloops` v4)
- the same claim (lower-cased, letters and digits only) is already recorded

A kept loop is stored with the exact quote and its source message, and logged as `open loop recorded from their own words` with the prompt `name@version`. The same call also lists the waiting loops with labels (`L1`, `L2`) and asks which of them their new messages settle. A loop is closed as `resolved` only when the label exists, the message is theirs and real, and the quote is in it, so a loop they bring up themselves is never asked about. A celebration is never settled by a message from before its day (`CELEBRATE_EARLY`): a birthday was once closed weeks early by an unrelated "all done".

**Kinds and times.** The kind sets when it falls due. A follow-up is the morning after the thing happens, at 10:00 local time. When nothing says when, it is 3 days after the day they said it, at 10:00. A celebration (their own occasion on a known day) is marked at 10:00 on the day. An encouragement (something big they face on a known day) comes at 8:30 on the day, just after quiet hours. A celebration or encouragement needs a day after today, or it is dropped. Dates are read from "tomorrow", "next week", "next month", weekday names, "weekend" and a written date such as a month and a day, taken as the next time it comes round. A plan for later today (scale `hours`) becomes a note-only loop, due 3 hours after the message, and is never a reach-out. A hedged plan (certainty `maybe`, such as "may watch a movie tonight") becomes a note-only loop too, by default (`COMPANION_HEDGED_PLANS=loose`, the owner's choice of 2026-10-24): offered as the loop note when they next write (at most twice, like any loop), never a reach-out. `off` makes it strict again, rejecting every plan that is not firm.

**The note when they write.** The due loop is a candidate for the one thing brought up on its own (`loop_candidate`, `Feature.mention`); the picker in `turn/mention.py` decides across plans and the calendar's days (ADR 0023). On a casual turn with nothing held and no earlier note asking them something, it brings up the best by rank (a celebration with their own day first, an encouragement next, a follow-up after any day), one a day across sources unless the new one ranks higher, so a morning follow-up never holds back a birthday. A plan goes in the system block. Rules for the loop itself:

- A follow-up is due from its time for 3 days. A celebration or encouragement is due on its day only.
- A loop is offered at most twice. After the first offer it is marked asked and can still be offered once more while unsettled.
- A celebration comes before an encouragement, which comes before a follow-up, then the most recently due.
- Never a sensitive loop.

The note is written from the loop's kind (`notes/loop-*`) and carries only the claim. Once the reply is stored, the loop is marked asked with the reason `open loop: offered as a note when they wrote`, and the same text is the decision key. A loop offered as a note is no longer open, so it is never also a reach-out.

**The learned pace (shadow, ADR 0023).** The picker is `turn/mention.py` (pure parts in
`core/turn/mentions.py`) and the read of how they met it is this feature's `met.py`. It covers every source: plans, the calendar's days and the check-in after a
heavy talk. The owner chose no fixed number a day: how often it brings something up is learned from how
they meet it. Once a turn is stored, when the companion's last message brought something up, their
message is read once for how it met it (`system/thread-met`):
picked up, brushed off or ignored, logged as `threads: how they met it` (a failed read is logged as not
read). The pace is a wait on a ladder of 4, 8, 16, 24, 48 and 96 hours that starts at 24; picked up is a
step down, brushed off a step up, ignored two, walked over the last 30 days so the newest answers decide
(`pace`). It never brings up more than 3 in 24 hours (`PACE_CEILING`, a backstop). For now
it only logs: each offer carries what the pace said (`pace` in its detail), and when something is due
and the day's count holds it while the pace would bring it up, `threads: the learned pace would bring
one up now (shadow)` is logged, at most once a day. The day's count still decides. On 12 invented turns the
judge was right 22 of 24 times and never read a brush-off as picked up (`evals/CHANGELOG.md`).

**Reaching out (shadow).** Every 15 minutes the initiative job (`background.py`) skips when the daily spend cap is reached, then asks the shared gate for every reach-out (`features/reach/gate.py` `hold`, through `holds` in `features/reach/run.py`, ADR 0023) and the pure gate in `gate.py`. The gate here expires open loops past their horizon (a follow-up 3 days after it fell due, `FOLLOW_UP_KEEPS` in `logic.py`, the longer of the note's 3 days and the reach-out's 2; a celebration or encouragement after its day) and picks the oldest due loop that is open, not note-only, not sensitive and, for a follow-up, no more than 2 days past due (`REACH_KEEPS`). Until 2026-11-07 the expiry was 2 days for both, so the note's third day was offered only for a loop already asked once. When the shared gate holds, the plan waits with its reason. It holds for the first of: `COMPANION_REACH=off`, a crisis turn under a day old (ADR 0022), their learned quiet hours (`core/rhythm.py`), a pretend scene, a chat active in the last 90 minutes, its last reach-out of any kind still unanswered (a shadow would-send counts as sent, so shadow shows what live would do), under six hours since its last of any kind, and its share of conversations at the dial (`docs/dev/initiative.md`). Until 2026-10-25 plans kept their own limits (fixed quiet hours of 23:00 to 08:00, one a day, 20 hours apart, a 72-hour back-off) and saw only their own reach-outs.

A hold is logged once per loop and per kind of hold as `held, would otherwise reach out` (`PLAN_HELD` in `core/reachout.py`, beside the key of the hold for its own reasons; `companion initiative` lists both) (the reason's numbers can change from tick to tick, such as the hour in quiet hours, so the kind is the key), so a hold lasting hours is one decision. When nothing holds it, a small model drafts the message (`system/openloops-draft`, purpose `initiative`). The draft is kept whole, however long, and dropped when it is empty, failed or reads as needy (`drafted` in `core/reachout.py`, the check every reach-out's draft passes, recorded by `record_draft` in `kit/reachdraft.py`). A dropped draft is logged as `open loop: the check-in draft was dropped, not sent` with why; nothing is recorded as sent, the loop stays open for the note when they write, and it is not drafted again. The tick records a shadow reach-out with its reason, marks the loop asked (`shadow reach-out, not sent`) and logs the decision `shadow, would send` (`PLAN_WOULD_SEND`). An offer as a note is an event of key `LOOP_OFFERED` (the `key` column from migration 0040; older events match by their reason). Nothing is sent: no code path sends a reach-out yet.

**Failures.** A failed extraction call leaves the bookmark where it was, so the same messages are read again next pass. A batch that fails 3 times is let go with the reason logged, so plans never block on one batch. A malformed answer is logged and ignored. A resolution that fails its checks only leaves the loop open, and the gate never asks before its time anyway. The plan reader also reads the companion's own messages for the promises it made (`features/promises/README.md`, shadow), in the same batch.

**Never.** It never asks about a sensitive or a not-firm plan, never about something said in a scene, and never before the time. Its reasons are written by code, never by a model (ADR 0003, 0006).

## Files

| File | What |
|---|---|
| `logic.py` | pure: which plans become loops, their kinds and times, the labels for settling, which loop becomes the note, the note text (`MAX_OFFERS`; the sensitivity cutoff is `core/sensitivity.py` `GUARDED_AT`) |
| `gate.py` | pure: which due loop to reach out about and which have expired, held with the shared gate's reason (`evaluate`) |
| `run.py` | effects: reading new messages for loops, the tick, the drafter, the loop's candidate for the picker (`loop_candidate`, `OPENLOOPS`) |
| `met.py` | effects: how they met what was brought up (`read_met`, `OPENLOOPS.after_turn`, which the dispatcher runs beside the reply), for the learned pace |
| `store.py` | its queries as `Threads` (`Store.part(Threads)`; the tables are in `store/sqlite/migrations/0012_open_loops.sql`). The reach-outs it writes are core storage (`store/sqlite/reach_outs.py`, `Store.add_reach_out`), because every kind of reach-out is read together |

## Prompts

- `system/openloops`: reads loops and which waiting loops are settled. A failed call keeps the batch for another try. A malformed answer is ignored.
- `system/openloops-draft`: writes the shadow check-in (judge `check-in-draft`, 30 s, spend `initiative`; schema and reading shared with the nudge draft in `core/reachout.py`). A failure gives an empty draft. The loop reader is the judge `loops` (120 s).
- `notes/loop-follow-up`: asks how it went, in the system block when a follow-up is due.
- `notes/loop-celebrate`: marks their occasion on the day.
- `notes/loop-encourage`: a word of cheering on the day.
- `system/thread-met`: how their next message met a thread it brought up. A failed read is logged as not read and leaves the pace as it was.

## Commands

- `uv run companion initiative`: lists the loops (state, kind, when), the shadow reach-outs, the holds, and the nudges (see `features/nudges/README.md`).

## Measured

- 2026-10-17: read-only pass over the recorded chat found about 8 plausible loops in 3 days, mostly low stakes (`evals/CHANGELOG.md`).
- 2026-10-17: replayed in shadow over the real history: 6 would-sends in 6 days at first, mostly mundane. Rejecting same-day and minute-scale loops, a 2-day horizon and the 18-word draft cut brought it to 4 in 4 days (`evals/CHANGELOG.md`).
- 2026-10-19: the note when they write, `notes/loop-*` v1, persona v40, 30 samples per fixture: a celebration on the day 30/30 wish them well, an urgent problem of theirs 30/30 never raised, a casual return about 23 of 30 ask how it went, 23 of 30 ask two questions (`evals/CHANGELOG.md`).
- 2026-10-24: of 33 candidates rejected in the previous five days for being hedged, minute-scale or not said for real, a blind judge found 2 a friend would ask about. That, and the owner's choice, is why hedged plans became note-only loops (`src/companion/prompts/CHANGELOG.md`, commit 7b06d22).

## Tests

`tests/features/threads/`
