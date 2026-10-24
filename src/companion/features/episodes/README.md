# Episodes (J12, J49)

Keeps a record of the times the two of them spent together, so when they say "last night" or come back after a while, it knows roughly what that time was like. Facts about them are memories and their plans are open loops, but what they did together had no record.

**Status:** live. `COMPANION_EPISODES`: `on` (default), `shadow` (logs what would be shown, shows nothing), `off`. The lines are written nightly at 04:00, by a command, and just before a reply when needed. The note rides the system block (it is the feature named `recent` in `registry.py`, and `recent` in `ORDER` in `turn/notes.py`).

## How it works

**Cutting the chat into stretches** (`stretches` in `logic.py`). The whole history is cut where there is a gap of 2 hours or more between messages (`GAP`). Each part is then cut again where the talk turns from everyday to a pretend scene, or back, but only when the new run lasts at least 20 messages (`SWITCH`). A shorter run folds into the one before it, or the one after it at the start, and neighbours of the same kind are joined.

**What code works out.** For each stretch: start, end, message count, the share of messages in a pretend scene (`scene_share`), and the top severity of their messages (read from the stored `listening` decisions, `top_severity`). The kind is `heavy` when the top severity is 2 or more (`SERIOUS`), else `scene` when half or more is pretend, else `everyday`. Firsts are "first pretend scene" and "first heavy talk" for the first stretch of that kind in the history. The model never decides these.

**The line.** `write_closed` in `run.py` writes a line for each stretch that has ended (no message for 2 hours) and has none from the current prompt. A newer prompt version writes the line again and the newest line wins in listings (`all_` in `store.py`), and the old ones stay. The writer `system/episode-gist` gets the facts (length, kind, share pretend) and the messages, each cut to 220 characters (`CUT`). A stretch over 40 messages shows only its first 13 and its last 27 (`LINES`). It writes one sentence of at most 25 words about the shape of that time and how it ended, with no details, names, dates or anything sexual or confided. Code stores a line only when it is non-empty and at most 35 words (`MAX_WORDS`), and a failed call or a rejected line leaves the stretch to be written next time. A warning is logged. Spend is tagged `episodes`.

**Showing it** (`recent_for_turn`, the look-up, then `recent_offer`, the note). Only on a turn that is not in a pretend scene, with a judge available and the switch not `off`. It acts when their message points at a time, or they come back after 3 hours (`GAP_BACK`, imported in `run.py` as `EPISODE_GAP`).
- "Points at a time" is `period`: "last night" or "this night" means 18:00 to 07:00, "yesterday" the day before, and "today", "this morning", "earlier", "tonight" or a phrase like "long day" the day so far. A day runs from 07:00 (`MORNING`) to 07:00, so at 3 a.m. "today" is still the day that is ending.
- When it acts, any stretch not yet written is written first, under an 8 second limit (`EPISODE_SECONDS`). If that fails or is late, the lines already recorded are still used.
- `recent` then picks: for a pointed time, the lines that overlap it, at most 3 (`SHOWN`), newest last. For a return after a gap, only the last recorded line. Each is shown with how long ago it was, said like a person ("earlier tonight", "last night", "yesterday", "on Monday").
- The note `notes/recent-times` lists them, in the system block, with the instruction to let it shape the answer and bring it up only if they do.
- The decision "episodes: what the two of them did recently, shown" is logged with the mode, why ("pointed at a time" or "back after a gap"), the lines and the note's `name@version`. In shadow its reason adds "(shadow, not sent)" and nothing reaches the talker.

Nothing in an episode line is ever shown to them. The log is append-only and a line is never deleted.

## Files

| File | What |
|---|---|
| `logic.py` | pure: cutting into stretches (`stretches`, `GAP`, `SWITCH`), kind and firsts, the writer's input (`transcript`, `facts`) and parse (`parse`, `MAX_WORDS`), which time their words point at (`period`, `when_said`), which lines to show (`recent`, `note`) |
| `run.py` | effects: writing the lines (`write_closed`), the look-up before the reply (`recent_for_turn`, `EPISODE_SECONDS`) and its note, as `EPISODES` |
| `store.py` | its queries: the `episodes` table, append-only, newest line per stretch (tables in `store/sqlite/migrations/`) |
| `cli.py` | `companion episodes`: list the lines, and `--write` to write new ones |

## Prompts

- `system/episode-gist`: writes one short sentence about the shape of a stretch. A failed call or a line over 35 words writes nothing and the stretch is tried again next time.
- `notes/recent-times`: shown in the system block on a turn where their words point at a time or they come back after a gap. It says what the two of them did recently, to shape the answer and not to be recited.

## Commands

- `uv run companion episodes`: the times they spent together, oldest first, with the line about each.
- `uv run companion episodes --write`: writes the lines for finished stretches that have none, then lists them (a model call).

## Measured

- 2026-10-22: the log cut into 25 stretches at a 2-hour gap or a 20-message change of frame. `system/episode-gist` v1 wrote too much detail, v2 gave one sentence each, mostly free of detail (`evals/CHANGELOG.md`).
- 2026-10-22: with `notes/recent-times`, replies asking them to explain what happened fell from 5/10 to 0/10 and 3/10 to 1/10, on two recorded turns at 10 draws each, read by eye (`evals/CHANGELOG.md`).
- 2026-10-22: the note was cleared as the cause of a claimed-news slip, since on that turn it ran in shadow and was never sent (`evals/CHANGELOG.md`).

## Tests

`tests/features/episodes/`
