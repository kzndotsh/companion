# Mood (ADR 0016, J5)

A mood that carries across hours and into the next day: cozy, tender or playful. Code owns it and it shows only in how the companion writes, never as a stated feeling and never as a pull to keep them talking.

**Status:** shadow by code default, `on` for the owner in `.env` (review by 2026-10-26, judged on a few days of flags on mood, then ADR 0016 accepted and the default made `on`). Switch: `COMPANION_MOOD` (`shadow` default, `on`, `off`). Runs before the reply as a note in the system block, and writes its effects once the turn is stored.

## How it works

**Effects, not a stored mood.** Each message of theirs can add effects to one state each. An effect has an amount, a half-life and a time, and is kept in an append-only table (`mood_effects`, written with the version of the numbers, `PARAMS_VERSION`). The mood is worked out from the effects when it is read, never stored, so it fades with nothing running, survives a restart and replays exactly. Only what they did can move it. There is no source for silence, a goodbye, a gap, a failed call, an undelivered reply or the spend cap. No model writes a number.

**What adds what.** Each source has a state, a half-life and a cap:

| Source | State | Half-life | Cap | What triggers it |
|---|---|---|---|---|
| `chat_span` | cozy | 4 h | 0.5 | 15 minutes or more chatted today (amount is minutes / 120) |
| `long_chat` | cozy | 24 h | 0.15 | an hour or more chatted today, a little warmth into the next day |
| `tone_sweet` | cozy | 3 h | 0.3 | the react judge read their previous message as sweet |
| `tone_funny` | playful | 2 h | 0.4 | the react judge read their previous message as funny |
| `energy` | playful | 2 h | 0.3 | typing energy 2 or more on a message rated not serious at all (0.1 per point) |
| `serious` | tender | 12 h | 0.8 | the listening judge rated the message 2 or 3 |
| `eased` | tender | 12 h | 0.2 | takes away from tender: play after something hard, added each time they joke again |

Minutes chatted are the gaps between today's messages that are no longer than 10 minutes, from local midnight. Typing energy counts stretched words, exclamation marks, emoji and emoticons, at most 2 of each kind, and counts nothing on a pasted block or a message with a sad or annoyed mark (`core/turn/energy.py`). The tone is the one judged on their previous message, because a message's own tone is judged beside the reply, after the mood is read. A serious turn (severity 2 or more) adds tender and nothing else, so every other state holds still. With no listening judgement (failed or off) a turn adds nothing, because an unread message could have been serious.

**Working out the mood.** A repeat from one source restarts its timer at the larger of what was left and what it brings, and never adds, so the order of reading cannot matter. Sources then add up within a state. Easing adds up instead, takes away from tender, and only counts after the latest effect that raised tender, so play before something hard does not soften the next one. Tender holds playful back: playful is zero while tender is at 0.3 or more, and weakened by it otherwise. Late at night (22:00 to 02:59 in their zone) cozy never falls below 0.35. Each strength is held to 1.0.

**What shows.** A state shows at 0.3 or more, at most two states, strongest first. Each shown state adds its line (`notes/mood-<state>`) to the `<notes>` in the system block, after the check-in note and before the hold, name and topic notes. No line is shown, whatever the mood, when:

- the turn is serious (it has the listening note)
- a pretend scene is in progress
- they are leaving (`core/turn/goodbye.py`, a pattern check, so a mood can never read as a pull to stay)

The lines describe behaviour, never name the mood word, and say never to describe its own state.

**Modes and the log.** Every turn but an `off` one logs a `mood` decision whose reason is written by code, such as `mood: cozy 0.42 (chat_span, tone_sweet) [on]`, or `mood: held, the turn is serious`. The detail holds the mode, the numbers' version, the strengths before and after, what this message added and the line. In `shadow` it works out and logs everything and writes the effects, but the model is sent nothing. In `on` it also sends the line. In `off` it does nothing. The effects are written once the turn is stored, so a failed turn adds none.

**Never.** It never moves on silence, a goodbye or a failed call, never shows on a serious turn, in a scene or on a goodbye, never changes the persona or a character's temperament, and never brings up what made it tender (held memories stay held).

**Notes outside the code's states.** `notes/mood-flat` and `notes/mood-buzzing` exist as files for measurement. Flat waits for the companion's own events (J6), and buzzing was set aside, so the code never sends either.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the states, what each message adds, how effects fade, the line and its reason, the replay (`RULES`, `PARAMS_VERSION`) |
| `run.py` | effects: the note and the effects written once the turn is stored (`MOOD`, `mood_offer`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0015_mood_effects.sql`) |
| `cli.py` | `companion mood`, `--replay DAYS` |

## Prompts

- `notes/mood-cozy`: calm, warm, unhurried, a bit shorter. Sent while cozy shows.
- `notes/mood-tender`: softer and more attentive after something hard, without bringing it up. Sent while tender shows.
- `notes/mood-playful`: teasing and joking come easily. Sent while playful shows.
- `notes/mood-flat`: measurement only, never sent by the bot.
- `notes/mood-buzzing`: dropped, never sent by the bot.

The code builds the name at run time as `notes/mood-<state>`. Mood has no judge of its own. It reads the listening severity and the react tone that other stages log.

## Commands

- `uv run companion mood`: the mood now, each state's strength and what holds it up. Writes nothing.
- `uv run companion mood --replay DAYS`: rebuilds what it would have been on each of their messages over the last DAYS days, with a row when what would show changes, from the same rules the bot uses.

## Measured

- 2026-10-19: forced `notes/mood-*` v1 on persona v31, 30 samples per cell. Replies moved mildly for four of five states, and the mood word leaked into replies (22 of 30 rain replies said "cozy"). 0 of 216 replies pulled at a goodbye or turned needy after silence (`evals/CHANGELOG.md`).
- 2026-10-19: lines v2 describe behaviour and say never to describe its own state. Playful judged playful 41% vs 1%, buzzing no change so dropped, tender 60 of 60 gentle after a hard event vs 54 of 60 with no line, stated mood 0 of 120 with any line (`evals/CHANGELOG.md`).
- 2026-10-19: persona v36 stops the volunteered mood, 4 of 30 stated its mood on v31 against 0 of 30 (`evals/CHANGELOG.md`).

## Tests

`tests/features/mood/`
