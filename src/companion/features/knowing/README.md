# Knowing (J48)

A map of what it knows about them: each memory is placed in a part of their life, and code picks the thinnest
part that is fine to ask about. It exists because it asked plenty of questions, but only about the thing just
said, so memory held almost nothing about hopes or values.

**Status:** shadow (review by 2026-10-26, judged on a week of picks that read right to the owner). No switch.
It labels after each memory pass and, on a casual turn, logs the pick beside the note step. Nothing reaches the
talker.

## How it works

Labelling. After each memory pass that stored new memories of theirs, up to 60 current memories without a label
are sent in one batch (`LABEL_BATCH`), each under a short ref. The model gives each a domain (identity,
people, daily, interests, history, hopes, values, inner) and a depth (surface, personal, core). Code keeps only
known refs and known values, one per memory. A failed call labels nothing and the same memories are tried again
next pass. The label is stored with the model and the prompt version.

Picking. On a casual turn, at most once in 24 hours (`MAP_EVERY`), and not while the ask-name note is offered
(the name comes first), code counts labelled memories per domain and picks the askable domain with the fewest.
A tie goes to the first in order: identity, people, daily, interests, history, hopes, values. The inner domain is
never asked about, only received. The depth is always surface until closeness can set it (T17). The pick is
logged after the turn is stored as `map: would ask about a gap (shadow)`, with the reason, the domain, the depth
and the counts. Nothing is picked when nothing is labelled yet.

The pick is the only output. How they want to be referred to and the name question are in `features/basics/`,
and the basic-fact question is in `features/hooks/`.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the domains it may ask about (`ASKABLE`), the label prompt and parse, the gap pick (`pick_gap`, `LABEL_BATCH`, `MAP_EVERY`) |
| `run.py` | effects: labelling (`label_new`), the pick on a turn (`map_offer`), the `Feature` (`KNOWING`) |
| `cli.py` | `companion map`: the table, the gap now and the recent picks, plus `label_now` for `--label` |

## Prompts

- `system/memory-map`: gives each memory a domain and a depth. A failed or empty answer labels nothing.

## Commands

- `uv run companion map [--label]`: counts by domain and depth, how many memories are unlabelled, the gap it would ask about now and the last 7 shadow picks. `--label` labels up to 10 batches first, which is a model call. It writes nothing else.

## Measured

Not measured yet.

## Tests

`tests/features/knowing/`
