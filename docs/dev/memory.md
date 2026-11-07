# Memory over time

How the companion turns the chat into memories, how it shows them to the model, how memory tidies
itself, and how the database is kept safe. What each feature adds to a memory (labels, context,
worth) is in its README under `src/companion/features/`.

## How a memory is made

Memory is written by the memory pass (`src/companion/memory/memory_pass.py`),
never during a reply. It runs once the chat has been quiet for 90 seconds (`memory/idle.py`), or at
once with `companion memory-pass`. Both run the same pass: its options are built once
(`compose.pass_options`): embedding the new memories, and what the features add (`PassParts.of`, all set
up from `Passing`): the same-memory check and the new-boundary question as each memory of theirs is
written (`Feature.memory_write`, reread), the open-loop read (`Feature.loops`, threads, with hedged
plans) with the promise read riding its batch and bookmark (`Feature.own_loop`, promises), and the
steps after every pass (`Feature.after_pass`: its own history and the scene memory). A rebuild runs
the plain parts (`plain_parts`: the strict open-loop read and the boundary question, no same-memory
check), because that check would match the memories it is replacing. It reads the messages not
yet read, in batches of 40 with the 4 before each for context, and asks a small model for candidate
memories.

A candidate is kept only if it rests on an exact quote from a message, with who said it and in which
frame (real, play, story or hypothetical) (ADR 0001, 0010). Anything said in play never becomes a
fact about their life. Nor does romantic, flirtatious or sexual behaviour between the two of them in
the chat (who invited, pushed or declined what, how far a scene went): only what they plainly say about
themselves there, such as a preference or a boundary, is kept. Every acceptance and rejection is a logged decision. The run log is the
bookmark, so a pass that crashes or runs twice reads nothing it already finished.

The same pass reads the companion's own messages for views it expressed. Those are gated before they
can reach the card (ADR 0009). A retired view goes on a rejected list, and the same view is not installed
again; memories about them have no such list yet (R15). A `/flag` does not retire every view the
flagged turn carried: a small model names the views the reply relied on or contradicted
(`system/views-implicated`), unclear means none, and only those are retired. The same pass also reads plans for open loops
(`src/companion/features/threads/README.md`). After a pass that stored new memories of theirs, each
feature's step runs in the registry's order: labelling the memory map, writing context
and judging worth; then the new memories are embedded. After a pass that stored new views of its own,
the lore step labels them (`src/companion/features/lore/README.md`).

After every pass, unless `COMPANION_HISTORY` is `off`, the history step reads the companion's own
messages after its own bookmark for small details of its own past, scenes included (a fact said in
passing counts, a scene event does not). Each is quoted, kept with its frame in its own append-only
tables, and checked three times against the character sheet and the stories already canon before it is
canon (ADR 0025, `src/companion/features/history/README.md`). It never reads or changes what is stored
about the user, and in step 1 nothing it keeps reaches the talker.

After every pass, unless `COMPANION_INTIMATE_MEMORY` is `off`, the scene memory step places memories that
have no lane yet in one, everyday or intimate, with an intimate one's stance (into, curious, a hard or
soft limit, style, aftercare). Each batch is read three times and a memory is intimate only when all
three agree; a floor in code keeps out anything that touches age or minors, anything from a turn the
minor check held, crisis-level memories, what they said while sharing something heavy, and any limit not
in their own plain words. The same step reads each ended pretend scene for how they tend to play, and a
pattern counts once quoted from two separate scenes (ADR 0026,
`src/companion/features/intimate/README.md`).

## How memory reaches the model

On every turn, a memory card is built from the current memories (`core/card.py`) and placed in the
system block. It holds up to 15 memories. Their boundaries and its promises come first. With
`COMPANION_FOCUS=on` (the default) the other places go to the memories closest to the moment: their
message, and the reply before it with it, embedded once a turn and compared with each memory's stored
vector (`features/focus/`). A memory that says what one already chosen says is skipped, a guarded memory
needs them sharing and a close match, a mildly personal one a close match, and a place nothing fills
stays empty. If the look-up is off, fails or takes over 2 seconds, the card is built the old way: up to
8 memories mentioned in the last 12 hours, newest first, then the rest by kind (tells, traits, states,
threads, preferences, events) and by how recently each was mentioned. Up to 3 older memories go in a
separate block, marked as possibly out of date.

A memory is never deleted (ADR 0002, 0008). It ages instead, measured from the last time it was
mentioned (`core/freshness.py`): a state goes stale after 14 days, a thread or a promise after 30, a
trait, a preference, a boundary or a tell after a year, and an event never does. Past half that time the card says it may
have changed. A stale memory leaves the card but stays in memory. A one-day
moment of daily life, and a personal event on a given date, leave the card a week after they were
last mentioned. A memory bound to the day it names (a plan for that day, having just woken up,
something expected on a date) leaves the card once that day is more than a day past, in the local
zone (`day_over` in `core/card.py`); it stays in memory, and the decision log says why it was left off.

Memories marked sensitive are shown only on turns where they are sharing something (severity 1 or
more), and with the focus on, only when they are close to the moment. The memories the card has no room for are logged once per turn. Memories that bear on the
message but are not on the card can still reach the model through the relevance look-up
and, when they ask it to remember, the asked look-up (`src/companion/features/recall/README.md`).

With `COMPANION_INTIMATE_MEMORY=on`, the default since 2026-11-05, a turn the roleplay talker answers gets
the roleplay card instead: the intimate memories and patterns nearest the moment and perhaps one thing they
are curious about, with their limits, what they are called and what they said about their own body sent
after the history. Every other turn leaves the intimate lane off the card, and both recall look-ups
(asked and near, `features/recall`) leave it out on every turn. In `shadow` both are logged and the card
is as above (ADR 0026).

## How memory tidies itself

Each night at 04:00 local, the night's memory work runs (`src/companion/memory/nightly.py`): the steps
the features declare (`Feature.nightly`), in the registry's order. Each step
runs on its own, so one failing does not skip the rest, and a night missed while the bot was down is
made up five minutes after it starts. Nothing runs that night once the daily spend cap is reached. The
steps are:

- the re-read (upkeep), which reads up to 40 week-old memories a night and closes faded passing moments
  or raises questions (`src/companion/features/upkeep/reread/README.md`); `COMPANION_REREAD=off` skips this
  step only
- grouping memories about one thing into merge questions (`src/companion/features/upkeep/merging/README.md`)
- retiring routine moments a week after they were last mentioned
  (`src/companion/features/upkeep/sort/README.md`)
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
