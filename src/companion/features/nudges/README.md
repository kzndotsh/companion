# Nudges (R1b)

A light nudge when they step away and stay gone much longer than they said, the way a friend might tease about a long shower. It exists so the owner can see how the looser rule behaves, so it only drafts and records.

**Status:** shadow (review by 2026-10-24, judged on drafts that do not read needy, at most two a day). Switch: `COMPANION_INITIATIVE` (`shadow` default, `off`). `off` stops both the read beside the turn of whether they stepped away and the 15-minute tick that drafts the nudge. Nothing is ever sent.

## How it works

**Reading a time away.** Beside any real turn that is not serious (not in a scene, severity below 2), a small model reads the message alone (`system/away`, 8 s limit, one try, purpose `nudge`). It answers one of four things: `brief` (leaving now for something short), `back` (leaving now and will return), `goodbye` (leaving for the night or for good), or `none`. It also gives the minutes it expects them to be away, which code clamps to between 10 and 180. A goodbye, `none` or a bad answer records nothing. A goodbye or no time away is a readable answer, not a failure. A call that fails or times out means no nudge for that message. A fallback model's answer counts. Each time away is a `away: they stepped away` decision (a policy decision) holding the kind, the minutes, their words, and the prompt `name@version`.

**The tick.** Every 15 minutes, after the open-loop tick and under the same daily spend cap, `tick_nudge` looks at their newest recorded time away. It holds, with a reason, for the first of these:

- no time away is recorded
- they wrote after it (any message from them cancels it)
- it was already nudged (one nudge per time away)
- more than 6 hours have passed, so it is past nudging
- not yet twice the minutes they said, and not yet an hour (the longer of the two)
- quiet hours, 23:00 to 08:00 local time (`Caps` in `core/reachout.py`, shared with open loops)
- already 2 nudges today

Nudges do not use the other reach-out caps (the daily one, the 20-hour gap, the 90 quiet minutes, the backoff). Only their own limits above apply. The reason is rendered from the numbers by code.

**The draft.** When nothing holds it, a small model writes one light message (`system/nudge-draft`, purpose `initiative`), given what they said and how many minutes ago it was. The prompt asks for under about twelve words and no guilt, no "I missed you" and no question about their silence. Code cuts a draft over 18 words to its first sentence only if that is a question, else drops it (`short_draft` in `core/reachout.py`). A failure gives an empty draft. The result is logged as the decision `nudge (shadow): would send` (an initiate decision) with the turn it is about, their words, the draft and the prompt. Nothing is sent. The same decisions set the one-per-time-away and two-a-day counts.

**Never.** It never nudges after a goodbye, in quiet hours, after they came back, or twice about one time away.

## Files

| File | What |
|---|---|
| `logic.py` | pure: reading the answer, how long to wait, when a nudge is due and why not, the draft prompt (`AWAY`, `WOULD_NUDGE`) |
| `run.py` | effects: the stepping-away read beside the turn, and the tick that drafts a nudge (`NUDGES`, `tick_nudge`) |

## Prompts

- `system/away`: whether the message steps away now, and for how long. A failed or unreadable answer means no nudge for that message.
- `system/nudge-draft`: writes the draft. A failure gives an empty draft.

## Commands

- `uv run companion initiative`: lists the times away it read and the nudges it would have sent, after the open loops.

## Measured

- 2026-10-20: `system/away` read all 855 real, not serious messages. The first wording found 37 times away but also read things already done. The second found 18, nearly all real. Replayed with the gate, no nudge in six days, because they always wrote again sooner (`evals/CHANGELOG.md`).

## Tests

`tests/features/nudges/`
