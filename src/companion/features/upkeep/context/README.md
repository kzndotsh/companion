# Context (J51)

A memory is written to stand alone, which strips the moment it came from. This adds a short note on what was
being talked about, shown beside the memory on the card.

**Status:** live. No switch. It runs after each memory pass and from a command.

## How it works

After each memory pass that accepted new memories of theirs, code takes current memories that want a note and have
none: a feeling or state, or a sensitive one (sensitivity 2 or more). Tastes, events and projects get none (unless sensitive).
Up to 20 per pass (`limit`), and 1000 from the command. For each, the model reads the memory and the messages
around its quote (6 before and 1 after) and writes one short clause. Code keeps it only if it is non-empty and
at most 25 words, drops a full stop and lowers the first letter. The clause is stored with the prompt version,
append-only. A memory whose quote is not in the history is skipped. A failed call is logged and skipped, and it
is tried again next pass. The card shows the note beside the memory.

The rule came from the owner's comparison of 19 memories alone, with their own words and with such a note. The
note won for feelings and sensitive memories (5 of the 6 such picks), the bare memory for tastes, events and
projects, and their words almost never.

## Files

| File | What |
|---|---|
| `logic.py` | pure: reading and limiting the note (`MAX_WORDS`) |
| `run.py` | effects: writing the notes (`write_missing`), the `Feature` (`CONTEXT`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/`) |
| `cli.py` | `companion memory context`: write the notes every memory wants (`write_now`) |

## Prompts

- `system/memory-context`: one clause, under 15 words, on what they were talking about. An empty or over-long answer writes nothing.

## Commands

- `uv run companion memory context`: writes the missing notes for every memory that wants one and prints the count and cost. A model call.

## Measured

- 2026-10-21: the owner's comparison of 19 memories chose the note for feelings and sensitive memories (5 of 6 picks), 53 backfilled (`TODO.md` J51 card, not in `evals/CHANGELOG.md`).

## Tests

`tests/features/upkeep/context/`
