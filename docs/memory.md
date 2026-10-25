# Memory over time

How the companion turns the chat into memories, how it shows them to the model, how memory tidies
itself, and how the database is kept safe. What each feature adds to a memory (labels, context,
names, worth) is in its README under `src/companion/features/`.

## How a memory is made

Memory is written by the memory pass, also called the slow loop (`src/companion/memory/slow.py`),
never during a reply. It runs once the chat has been quiet for 90 seconds. It reads the messages not
yet read, in batches of 40 with the 4 before each for context, and asks a small model for candidate
memories.

A candidate is kept only if it rests on an exact quote from a message, with who said it and in which
frame (real, play, story or hypothetical) (ADR 0001, 0010). Anything said in play never becomes a
fact about their life. Every acceptance and rejection is a logged decision. The run log is the
bookmark, so a pass that crashes or runs twice reads nothing it already finished.

The same pass reads the companion's own messages for views it expressed. Those are gated before they
can reach the card (ADR 0009). The same pass also reads plans for open loops
(`src/companion/features/openloops/README.md`). After a pass that stored new memories of theirs, each
feature's step runs in the registry's order: labelling the memory map, listing names, writing context
and judging worth; then the new memories are embedded. After a pass that stored new views of its own,
the lore step labels them (`src/companion/features/lore/README.md`).

## How memory reaches the model

On every turn, a memory card is built from the current memories (`core/card.py`) and placed in the
system block. It holds up to 15 memories. Their boundaries and its promises come first, then up to 8 memories
mentioned in the last 12 hours, newest first, so what they said this evening is in view; then the rest
by kind (tells, traits, states, threads, preferences, events) and by how recently each was mentioned. Up to 3 older
memories go in a separate block, marked as possibly out of date.

A memory is never deleted (ADR 0002, 0008). It ages instead, measured from the last time it was
mentioned (`core/freshness.py`): a state goes stale after 14 days, a thread or a promise after 30, a
trait or a preference after a year, and an event never does. Past half that time the card says it may
have changed. A stale memory leaves the card but stays in memory. A one-day
moment of daily life, and a personal event on a given date, leave the card a week after they were
last mentioned.

Memories marked sensitive are shown only on turns where they are sharing something (severity 1 or
more). The memories the card has no room for are logged once per turn. Memories that bear on the
message but are not on the card can still reach the model through the relevance look-up
(`src/companion/features/relevance/README.md`).

## How memory tidies itself

Each night at 04:00 local, the night's memory work runs (`src/companion/memory/nightly.py`). Each step
runs on its own, so one failing does not skip the rest, and a night missed while the bot was down is
made up five minutes after it starts. Nothing runs that night once the daily spend cap is reached. The
steps are:

- the memory check, which reads up to 40 week-old memories a night and closes faded passing moments
  or raises questions (`src/companion/features/consolidate/README.md`); `COMPANION_CONSOLIDATE=off` skips this
  step only
- grouping memories about one thing into merge questions (`src/companion/features/merging/README.md`)
- retiring routine moments a week after they were last mentioned
  (`src/companion/features/worth/README.md`)
- writing a line for each finished stretch of chat (`src/companion/features/episodes/README.md`)

Memory changes itself only where a judge has matched the owner's own review (ADR 0019). Everything
else becomes a question. `uv run companion memory review` asks the owner the questions the checks
raised, and nothing is merged automatically.

## Backups

The database and the character sheets are snapshotted at every start (before migrations) and once a
day (`src/companion/backups.py`), and each database copy is checked. The newest 7 daily copies and 7
others are kept in `data/backups/` (`COMPANION_BACKUP_DIR`).

`uv run companion backup --restore FILE` refuses to run while the bot is running. It keeps the current
database first, and replaces nothing unless the copy passes its check.
