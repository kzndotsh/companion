# Names (fetch on mention)

When their message names a pet, a person or a band memory knows, the card may hold nothing about it, since it
shows about fifteen of hundreds of memories. This feature finds those misses in shadow, to see whether a
look-up on mention is worth building.

**Status:** shadow (review by 2026-10-27, judged on how often the card missed a memory about a name they used).
No switch. It lists names after each memory pass and matches them beside the turn. Nothing reaches the talker.

## How it works

Listing. After each memory pass that stored new memories of theirs, up to 60 current memories about them (not its own views) not yet read are
sent in one batch (`BATCH`), each under a short ref, with the names already known so the model reuses them. The
model lists each specific named thing (a person, pet, place, band, song, show, game, project or brand) with
its other ways of being said and the refs of the memories about it. Code keeps only refs it showed and terms
worth matching: at least 3 letters and not only common words. Every memory in the batch is marked read, whether
or not it had a name, so each is read once. A failed call reads nothing and is tried again next pass. A
malformed answer is ignored with a warning and the batch is tried again.

Matching. On a turn that was listened to, in a real frame (not a scene), code takes the current memories that
are safe to show: stated for real, and sensitive ones only when the listening read says they are sharing
(severity 1 or more), else only below the hold level of 2. It matches their message against each name's terms
as whole words, ignoring case. For each name found it logs `names (shadow): they named something memory knows`
with the names, the memories the card left out (`would_add`) and the ones already on it (`on_card`, which
counts usable, held and older). A name with no memories left alive is skipped.

Tables are append-only (`belief_names` and `name_reads`). Nothing is ever sent to the talker.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the names prompt and parse, the index of names over current memories, whole-word matching (`BATCH`, `MIN_LETTERS`, `SHADOW`) |
| `run.py` | effects: reading new memories (`read_names`), the match on a turn (`named_in_turn`), the `Feature` (`NAMES`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |
| `cli.py` | `companion names`: the list and the counts, plus `read_now` for `--read` |

## Prompts

- `system/memory-names`: lists the names in a batch of memories with their other words and refs. A failed call or a malformed answer reads nothing.

## Commands

- `uv run companion names [--read]`: each name with how many memories are about it and its words, how many turns named something, on how many the card lacked a memory, and how many memories are not read yet. `--read` reads new memories first (up to 10 batches, a model call).

## Measured

- 2026-10-20: all 199 memories read for $0.0014, 21 names listed. Replayed over past messages the whole-word match found real mentions and one false one, a song title that is an everyday word (`evals/CHANGELOG.md`).
- 2026-10-20: since the restart, one turn named something memory knows and the card lacked it, but relevance had already picked that memory first (`evals/CHANGELOG.md`).

## Tests

`tests/features/names/`
