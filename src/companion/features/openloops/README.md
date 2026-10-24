# Open loops (J15, ADR 0015)

Things they said about their own near future that a friend would ask about later, such as a plan, an appointment or something they are waiting on. It brings one up when they next write, and in shadow it works out when it would reach out first.

**Status:** the note when they write is live. Reaching out is shadow (review by 2026-10-31, judged on would-sends that read right to the owner, none in quiet hours or mid-chat). Switch: `COMPANION_INITIATIVE` (`shadow` default, `off`), which stops only the 15-minute tick. Reading plans (in the slow loop's batch, after a memory pass) and the note (before the reply) run whatever it says.

## How it works

**Reading plans.** The open-loop pass runs inside the slow loop's batch, after the beliefs, with one small-model call per batch (`system/openloops`, purpose `loops`). It has its own bookmark (`open_loop_runs`), so it never depends on the belief pass. It reads up to 40 messages per batch, with 4 messages of earlier context, and up to 3 batches per pass. The model only labels: the quote, a short claim, when it happens as they said it, a scale (`minutes`, `hours`, `days`, `unknown`), a sensitivity from 0 to 3, a certainty (`firm`, `maybe`, `wish`), whether it is about the companion, and a kind. Code decides what to keep. A candidate is dropped, with the reason logged, when:

- the cited message is not found, or no single message of theirs holds the quote
- it was not said by them for real (a scene or the companion's own words)
- the quote is not word for word in their message
- the scale is `minutes`, or it is about the companion or the chat
- the certainty is not `firm`, or the kind is unknown
- a celebration or encouragement has no day after today to land on
- sensitivity is 2 or more, so a sensitive plan is never raised on its own
- the claim is empty or over 160 characters
- the follow-up time was already more than 3 days past
- the same claim (lower-cased, letters and digits only) is already recorded

A kept loop is stored with the exact quote and its source message, and logged as `open loop recorded from their own words` with the prompt `name@version`. The same call also lists the waiting loops with labels (`L1`, `L2`) and asks which of them their new messages settle. A loop is closed as `resolved` only when the label exists, the message is theirs and real, and the quote is in it, so a loop they bring up themselves is never asked about.

**Kinds and times.** The kind sets when it falls due. A follow-up is the morning after the thing happens, at 10:00 local time. When nothing says when, it is 3 days after the day they said it, at 10:00. A celebration (their own occasion on a known day) is marked at 10:00 on the day. An encouragement (something big they face on a known day) comes at 8:30 on the day, just after quiet hours. A celebration or encouragement needs a day after today, or it is dropped. Dates are read from "tomorrow", "next week", "next month", weekday names, "weekend" and a written date such as a month and a day, taken as the next time it comes round. A plan for later today (scale `hours`) becomes a note-only loop, due 3 hours after the message, and is never a reach-out.

**The note when they write.** On a casual turn (read as not serious, not in a scene, not a goodbye) with no name question, no check-in and nothing held, one due loop becomes a note in the system block (`pick_note`). It sits after the name and memory-map notes and before the topic notes. Rules:

- A follow-up is due from its time for 3 days. A celebration or encouragement is due on its day only.
- A loop is offered at most twice. After the first offer it is marked asked and can still be offered once more while unsettled.
- At most one loop note per 24 hours.
- A celebration comes before an encouragement, which comes before a follow-up, then the most recently due.
- Never a sensitive loop.

The note is written from the loop's kind (`notes/loop-*`) and carries only the claim. Once the reply is stored, the loop is marked asked with the reason `open loop: offered as a note when they wrote`, and the same text is the decision key. A loop offered as a note is no longer open, so it is never also a reach-out.

**Reaching out (shadow).** Every 15 minutes the tick in `daemon.py` skips when the daily spend cap is reached, then asks the pure gate in `gate.py`. The gate expires open loops past their horizon: a follow-up 2 days after it fell due, a celebration or encouragement after its day. It picks the oldest due loop that is open, not note-only and not sensitive. Then it holds, with a reason rendered from the numbers, for the first of these:

- quiet hours, 23:00 to 08:00 local time
- a pretend scene in progress
- already one reach-out today (the cap is 1 a day)
- 2 reach-outs in a row went unanswered, so it waits for them to write first
- the last reach-out went unanswered and fewer than 72 hours have passed
- the last reach-out was under 20 hours ago
- the chat was active under 90 minutes ago

These numbers live in `Caps` in `core/reachout.py`, shared with nudges. Quiet hours are shared with nudges. The cap, the gap, the 90 minutes and the backoff are used by open loops only. A hold is logged once per loop and reason as `held, would otherwise reach out`, so a hold lasting hours is one decision. When nothing holds it, a small model drafts the message (`system/openloops-draft`, purpose `initiative`) and any failure gives an empty draft. A draft over 18 words is cut to its first sentence only if that is a question, else dropped. The tick records a shadow reach-out with its reason, marks the loop asked (`shadow reach-out, not sent`) and logs the decision `shadow, would send`. Nothing is sent: no code path sends a reach-out yet. The unanswered counts only look at live reach-outs, so in shadow they stay at zero. That is by design (ADR 0015): a draft that was never sent could not be answered, so it never counts toward the back-off.

**Failures.** A failed extraction call leaves the bookmark where it was, so the same messages are read again next pass. A batch that fails 3 times is let go with the reason logged, so plans never block on one batch. A malformed answer is logged and ignored. A resolution that fails its checks only leaves the loop open, and the gate never asks before its time anyway. The plan reader also reads the companion's own messages for the promises it made (`features/promises/README.md`, shadow), in the same batch.

**Never.** It never asks about a sensitive or a not-firm plan, never about something said in a scene, and never before the time. Its reasons are written by code, never by a model (ADR 0003, 0006).

## Files

| File | What |
|---|---|
| `logic.py` | pure: which plans become loops, their kinds and times, the labels for settling, which loop becomes the note, the note text (`SENSITIVE`, `MAX_OFFERS`) |
| `gate.py` | pure: whether to reach out now and about what, with the reason (`evaluate`) |
| `run.py` | effects: reading new messages for loops, the tick, the drafter, the note (`OPENLOOPS`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0012_open_loops.sql`) |

## Prompts

- `system/openloops`: reads loops and which waiting loops are settled. A failed call keeps the batch for another try. A malformed answer is ignored.
- `system/openloops-draft`: writes the shadow check-in. A failure gives an empty draft.
- `notes/loop-follow-up`: asks how it went, in the system block when a follow-up is due.
- `notes/loop-celebrate`: marks their occasion on the day.
- `notes/loop-encourage`: a word of cheering on the day.

## Commands

- `uv run companion initiative`: lists the loops (state, kind, when), the shadow reach-outs, the holds, and the nudges (see `features/nudges/README.md`).

## Measured

- 2026-10-17: read-only pass over the real chat found about 8 plausible loops in 3 days, mostly low stakes (`evals/CHANGELOG.md`).
- 2026-10-17: replayed in shadow over the real history: 6 would-sends in 6 days at first, mostly mundane. Rejecting same-day and minute-scale loops, a 2-day horizon and the 18-word draft cut brought it to 4 in 4 days (`evals/CHANGELOG.md`).
- 2026-10-19: the note when they write, `notes/loop-*` v1, persona v40, 30 samples per fixture: a celebration on the day 30/30 wish them well, an urgent problem of theirs 30/30 never raised, a casual return about 23 of 30 ask how it went, 23 of 30 ask two questions (`evals/CHANGELOG.md`).

## Tests

`tests/features/openloops/`
