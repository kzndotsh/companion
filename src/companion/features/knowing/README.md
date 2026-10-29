# Knowing (J48)

A map of what it knows about them: each memory is placed in a part of their life, and code picks the thinnest
part that is fine to ask about. It exists because it asked plenty of questions, but only about the thing just
said, so memory held almost nothing about hopes or values.

**Status:** live since the review of 2026-10-29 (a week of shadow picks read right to the owner). No switch.
It labels after each memory pass and, on a casual turn at most once in three days, sends a note to ask one light
question about the thinnest part.

## How it works

Labelling. After each memory pass that stored new memories of theirs, up to 60 current memories without a label
are sent in one batch (`LABEL_BATCH`), each under a short ref. The model gives each a domain (identity,
people, daily, interests, history, hopes, values, inner) and a depth (surface, personal, core). Code keeps only
known refs and known values, one per memory. A failed call labels nothing and the same memories are tried again
next pass. The label is stored with the model and the prompt version.

Picking. On a casual turn, at most once in three days (`MAP_EVERY`), and not while a note before it asks them
something (`asking`, so the name comes first), code counts labelled memories per domain and picks the askable domain with the fewest.
A tie goes to the first in order: identity, people, daily, interests, history, hopes, values. The inner domain is
never asked about, only received. The depth is always surface until closeness can set it (T17). The pick
becomes `notes/map-ask`, with the part filled in from `PART`, and the offer says it asks (`Offer(asks=True)`), so
what it would bring up on its own waits that turn. Once the turn is stored it is logged as `map: offered to ask
about a gap`, with the reason, the domain, the depth and the counts. Nothing is picked when nothing is labelled
yet. Picks from the shadow week (19 to 27 Oct) stay in the log as `map: would ask about a gap (shadow)`.

The note is the only output. How they want to be referred to and the name question are in `features/basics/`,
and the basic-fact question is in `features/hooks/`.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the domains it may ask about (`ASKABLE`) and how each reads (`PART`), the label prompt and parse, the gap pick (`pick_gap`, `LABEL_BATCH`, `MAP_EVERY`) and its note (`ask_note`) |
| `run.py` | effects: labelling (`label_new`), the note on a turn (`map_offer`), the `Feature` (`KNOWING`) |
| `cli.py` | `companion map`: the table, the gap now and the recent picks, plus `label_now` for `--label` |

## Prompts

- `system/memory-map`: gives each memory a domain and a depth. A failed or empty answer labels nothing.
- `notes/map-ask`: asks one light question about the thinnest part, once, after reacting to what they said.

## Commands

- `uv run companion map [--label]`: counts by domain and depth, how many memories are unlabelled, the gap it would ask about now and the last 7 picks, offered or from the shadow week. `--label` labels up to 10 batches first, which is a model call. It writes nothing else.

## Measured

- 2026-10-29 review: 7 shadow picks over 19 to 27 Oct, all people (6 of 235 memories), read right by the owner.

## Tests

`tests/features/knowing/`
