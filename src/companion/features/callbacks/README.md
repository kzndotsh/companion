# Callbacks (J2)

A score for whether a reply brought up a memory on its own, and whether that landed. It measures replies. Nothing it finds reaches the talker.

**Status:** measurement only. No switch. It runs only from `uv run companion callbacks`.

## How it works

Users value the companion bringing up something minor from days ago, unprompted, correctly and at a fitting moment. A wrong callback hurts more than a missed one, so the report puts precision first. Word overlap cannot find callbacks (on 570 real turns it found 6, all false matches), so a judge reads each reply.

The command looks at turns since a start time (`--days`, default 7) that have a stored card and a reply and no verdict yet. For each, oldest first, it takes the memories the card held (`core/card.py` `memories_from_card`) and labels them `m1`, `m2` and so on. A turn whose card has no memories is skipped. The judge is given the last 7 stored messages up to and including theirs, the labelled memories and the reply.

The judge answers with five fields: `callback`, `memories` (labels), `accurate`, `fitting` and `forced`. A reply landed only when it is a callback, accurate, fitting and not forced. An answer is unreadable when a flag is not a boolean, when `memories` is not a list, or when it claims a callback but names no known label. Unlabelled names are dropped.

Spend is capped (`--cap`, default 0.10 dollars). Before each turn the loop stops if the spend so far has reached the cap. A call that raises, or an unreadable answer, skips that turn with a log line and leaves it for the next run. A verdict is stored once per turn, append-only, with the judge model and the prompt version, so a later run pays only for new turns. The call goes straight through `extract` with `purpose("callbacks")`, not through the judge runner in `loops/ask.py`.

The report shows replies checked, callbacks found, and how many landed, were wrong (not accurate) or were forced or out of place. It then lists up to the last 8 callbacks, each with a clipped reply and the first memory it used.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the judge prompt (`PROMPT`), the schema, `Check` and whether it landed, the prompt text, parsing a verdict, the report |
| `run.py` | effects: judging unchecked turns within a spend cap, each turn once (`check_new`) |
| `store.py` | its queries: unchecked turns, adding a verdict, verdicts since a time (table in `store/sqlite/migrations/0014_callback_checks.sql`) |
| `cli.py` | `companion callbacks`: judge recent replies within a cap, then print the report (`judge_now`) |

## Prompts

- `system/callback-judge`: decides whether the reply used a specific detail from a memory that was not in the recent messages, and whether it was accurate, fitting and not forced. A broad theme does not count. An unreadable answer means the turn is left unjudged for the next run.

## Commands

- `uv run companion callbacks [--days N] [--cap USD]`: judges new replies from the last N days (default 7) up to the cap (default 0.10), then prints the report.

## Measured

- 2026-10-18: first reading on 338 real replies for $0.05. Judge v1 found 6 callbacks. By eye 2 were genuine and landed, 1 wrong and 1 forced, and 2 loose links counted as landed, so v2 requires a specific detail. Fixture traps 12/12 each. A clear opening was taken 4/20 (`evals/CHANGELOG.md`).

## Tests

`tests/features/callbacks/`
