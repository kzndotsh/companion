# Reaching out for its own reasons (ADR 0021)

A friend who likes you writes first now and then: because something made them think of you, because it is the time you usually talk, or because they simply missed you. This lets the companion do that, with code choosing the reason, the moment and the one thing it is about, and a model only writing the words.

**Status:** shadow (review by 2026-10-30, judged on drafts the owner marks as wanted, landing at sensible times in their learned hours, none needy or guilt-laden). Switches: `COMPANION_INITIATIVE` (`shadow` default, `off`) runs or stops the whole 15-minute tick; `COMPANION_REACH` sets the dial (`warm` default; `off`, `rare`, `light`, `normal`, `clingy`). Nothing is ever sent: no code path here sends a message.

## How it works

**Their rhythm, learned.** Each tick, code reads the times of their own messages over the last 14 days (`core/rhythm.py`). A conversation starts after a pause of 2 hours or more. From those it takes their pauses between conversations and the 75th percentile of them, the hours of the day they write (for each local hour, the days they wrote in it, as a share of their busiest hour's days), and their quiet hours (hours written in on under a tenth of that). Before there is history it uses a baseline: a 12-hour pause, usual hours 9 AM to 10 PM and quiet hours 11 PM to 8 AM, in the machine's named zone. The two are blended by how many conversations it has seen: the weight on their own numbers is the count over 20, full from 20. An hour is usual when its blended score is at least one half, and quiet when its blended quiet score is at least 0.9, so someone who writes at night gets quiet hours in the day. The pause past which it may miss them is the blend of 12 hours and their 75th percentile, never under 8 hours. Every decision carries these numbers and the weight.

**The kinds, in order.** Every kind is weighed on every tick and logged with why it applies or not; the first that applies is the reason:

1. A plan of theirs: the open-loop tick (`features/threads/README.md`). If it would send this tick, nothing more is done.
2. Stepping away: the nudge tick (`features/nudges/README.md`), the same.
3. A time they keep: they wrote within the same local hour on at least 5 of the last 7 days, it is that hour now, and it has not said hi at their time in the last 3 days.
4. A thought: one thing it knows, chosen by code: a memory of theirs that is a thread or a like (sensitivity 0 or 1 only, never 2 or 3, never from a scene), one of its own tastes (ADR 0020), or the gist of an everyday stretch of chat from the last 7 days. The pick is the same for the same day (a hash of the date and the thing's id), so a replay or a test is stable, and a thing is not used twice in 14 days. It applies at a usual hour once the pause is at least half the missing-them pause, at most once a day.
5. Missing them: the pause since their last message is past the learned pause and it is one of their usual hours.

The one thing is chosen for every kind and handed to the drafter with it, so a time they keep or missing them is still about one specific thing when there is one.

**The gate.** When a kind applies, a pure gate (`gate.py`) holds it for the first of these, in order, with a reason written from the numbers:

1. the dial is `off`
2. a turn the crisis path read as concern or urgent, acted on, under a day old (`core/crisis.py` `reach_held`, ADR 0022; the hold is logged only once `COMPANION_CRISIS` is on, so in shadow it changes nothing)
3. one of their quiet hours (learned)
4. a pretend scene in progress
5. the chat was active in the last 90 minutes
6. its last reach-out is unanswered: they have not written since it, so it waits for them to write first
7. its last reach-out, or a dropped draft, was under 6 hours ago
8. the share of conversations it started in the last 14 days is at or above the dial's target
9. the daily spend cap is reached

"Its reach-outs" here are all of them: these, the open-loop reach-outs and the nudges, shadow or live.

**The dial.** `COMPANION_REACH` is the share of conversations it may start over the last 14 days: `rare` 1/8, `light` 1/5, `normal` 1/4, `warm` 1/3 (the default), `clingy` 1/2. In shadow a would-send counts as a conversation it started and as a message they have not answered, so shadow holds and paces the way live would. Code follows how they answer: when its last reach-out was answered later than their usual pause, or in 3 words or fewer (their words in the 10 minutes after their first reply), the dial steps down one level (`warm` to `normal`, `rare` to `off`) until they start a conversation themselves after that answer. The step down is logged once as `reach out: dial stepped down`. Not answering at all is the unanswered hold above. Nothing counts streaks or optimises how often they write.

**The draft.** Only when every check has passed, a small model writes one message (`system/reach-draft`, purpose `initiative`, 20 s, one try), given the kind and the one thing and nothing about how long it has been. Then code checks it: the draft is kept whole however long (`draft_text` in `core/reachout.py`); an empty one is dropped, and a draft is dropped, never rewritten, when it mentions waiting, being forgotten or ignored, how long they were gone, asks why they went quiet or whether they are okay, adds urgency (asap, reply, guess what, `!!`, streaks), or makes them responsible for how it feels (`needy` in `logic.py`). A dropped draft is recorded with why and counts for the 6-hour gap, so a bad draft is not retried every tick.

**Recording.** A would-send is a row in the append-only `own_reach_outs` table (kind, the thing's id, the draft, mode `shadow`, and the rhythm, the share, the dial and the kinds considered) and an initiate decision `reach out (shadow): would send`. A dropped draft is a row with mode `dropped` and a decision `reach out: draft dropped`. A hold is a decision `reach out: held` with its hold and the same numbers, logged once while the same kind is held for the same reason, so a hold lasting hours is one decision.

**Never.** It never reaches out about a sensitive memory, in their quiet hours, mid-chat or in a scene, twice while one is unanswered, or with a line about their silence. A mood never triggers one (ADR 0016), and a model never decides when to speak.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the dial and its targets, the kinds and their precedence, the one thing, the needy check, the draft input (`Dial`, `Kind`, `consider`, `choose`, `pick_thing`, `needy`) |
| `gate.py` | pure: the share of conversations it started, how its last was answered, the step down, and the holds in order (`hold`, `share`, `pace`) |
| `run.py` | effects: reads the store, learns the rhythm, the tick and the draft (`tick_reach`, `Reacher`) |
| `store.py` | its queries (the table is in `store/sqlite/migrations/0032_own_reach_outs.sql`) |
| `cli.py` | its part of `companion initiative` |

## Prompts

- `system/reach-draft`: writes the one message for the kind and the thing. A failure or an unreadable answer gives no draft, recorded as dropped.

## Commands

- `uv run companion initiative`: after the open loops and nudges, the learned rhythm (and how much is baseline), the share against the dial, each would-send with its time, kind and draft, the dropped drafts, and the holds by reason.

## Measured

- Nothing measured yet: built and accepted 2026-10-24 in shadow (ADR 0021), and `system/reach-draft` has had no eval or bake-off. The 2026-10-24 shadow review of the older reach-out and nudge ticks found nothing drafted yet to judge. The owner reads the would-sends for three to five days before any of it goes live.

## Tests

`tests/features/reach/` and `tests/core/test_rhythm.py`
