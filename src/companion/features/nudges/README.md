# Nudges (R1b)

A light nudge when they step away and stay gone much longer than they said, the way a friend might tease about a long shower. It exists so the owner can see how the looser rule behaves, so it only drafts and records.

**Status:** shadow (review by 2026-11-03, judged on drafts that do not read needy, at most two a day). Switch: `COMPANION_INITIATIVE` (`shadow` default, `off`). `off` stops both the read beside the turn of whether they stepped away and the 15-minute tick that drafts the nudge. Nothing is ever sent.

## How it works

**Reading a time away.** A time away is a `leaving` label from the reader of what is happening with them now (`features/now/README.md`, ADR 0024): beside any real turn that is not serious, a small model labels their message (`soon`, `leaving`, `back`, `done`), with the minutes; the newest `leaving` in the last six hours is the time away (`aways` in `logic.py`). Until 2026-10-25 nudges had their own reader (`system/away`, retired), which also told a brief time away from one they said they would come back from; the two were treated alike, so the label is now only `leaving`.

**The tick.** Every 15 minutes, after the open-loop tick and under the same daily spend cap, `tick_nudge` (`daemon.py`) looks at their newest recorded time away. It is skipped on a tick when a plan check-in would go. It holds, with a reason, for the first of these:

- no time away is recorded
- they wrote after it (any message from them cancels it)
- it was already nudged (one nudge per time away)
- more than 6 hours have passed, so it is past nudging
- not yet twice the minutes they said, and not yet an hour (the longer of the two)
- already 2 nudges today
- the shared gate every reach-out asks holds it (`holds` in `features/reach/run.py`, ADR 0023, passed in by the daemon): a crisis turn under a day old, their learned quiet hours, a scene, a chat active in the last 90 minutes, its last reach-out of any kind unanswered, under six hours since its last of any kind, or its share of conversations at the dial

Since 2026-10-25 nudges use the shared gate instead of fixed quiet hours of 23:00 to 08:00. One effect: a short time away is nudged no sooner than 90 minutes after the last message, the shared gate's active chat, where an hour was enough before. The reason is rendered from the numbers by code.

**The draft.** When nothing holds it, a small model writes one light message (`system/nudge-draft`, purpose `initiative`), given what they said and how many minutes ago it was. The prompt asks for under about twelve words and no guilt, no "I missed you" and no question about their silence. Code keeps the draft whole, however long, and drops one that is empty, failed, or reads as needy (`checked` in `core/reachout.py`, the check every reach-out's draft passes). A dropped draft is logged as `nudge (shadow): draft dropped, not sent` with why, does not count as a nudge, and that time away is not drafted again. A kept one is logged as the decision `nudge (shadow): would send` (an initiate decision) with the turn it is about, their words, the draft and the prompt. Nothing is sent. A drafted nudge also counts as the tick's first reach-out, so the own-reasons reach-out (ADR 0021) does not draft in the same tick. The same decisions set the one-per-time-away and two-a-day counts.

**Never.** It never nudges after a goodbye, in quiet hours, after they came back, or twice about one time away.

## Files

| File | What |
|---|---|
| `logic.py` | pure: reading the answer, how long to wait, when a nudge is due and why not, the draft prompt (`AWAY`; the nudge's key `WOULD_NUDGE` is in `core/reachout.py`, so other reach-outs can count it) |
| `run.py` | effects: the stepping-away read beside the turn, and the tick that drafts a nudge (`NUDGES`, `tick_nudge`) |

## Prompts

- `system/nudge-draft`: writes the draft. A failure gives an empty draft.

## Commands

- `uv run companion initiative`: lists the times away it read and the nudges it would have sent, after the open loops.

## Measured

- 2026-10-20: `system/away` read all 855 real, not serious messages. The first wording found 37 times away but also read things already done. The second found 18, nearly all real. Replayed with the gate, no nudge in six days, because they always wrote again sooner (`evals/CHANGELOG.md`).
- 2026-10-24 (first review, commit 9f5980d): neither this nor reaching out had drafted anything, because every time away ended within a minute, so there was nothing to judge. Review moved to 2026-10-31.

## Tests

`tests/features/nudges/`
