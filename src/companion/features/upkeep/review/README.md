# Review

The one place the owner answers what upkeep found. The merge proposals and the re-read's and the sorter's
questions all land in one queue, asked in `companion memory review`.

**Status:** live. No switch. It runs from a command.

## How it works

The queue is the unanswered merge proposals first, then the checks: `out_of_date`, `overstated`, a passing memory
that is sensitive, a new rule for how to treat them, a remark about the bot and a routine moment the sorter would
let go, then conflicting pairs. A conflict between two memories that a pending merge would join is held back, since
pieces of one moment read as a contradiction when apart. Each answer is recorded (a merge answer as a typed `Answer` in `merging/logic.py`, stored as the same text as before, read back by `repick`; the questions' wording is `WHY` in `reread/logic.py` and `sort/logic.py`) and a retire goes through the
logged retire path (`kit/curate.py`); nothing is deleted, and a question skipped changes nothing. The owner can stop
with `[q]uit` and a question waits for another time. A memory that is gone is answered as gone.

## Files

| File | What |
|---|---|
| `cli.py` | `companion memory review`: the queue (`_pending`), each question and its answer, and the sitting (`review`) |

## Prompts

None.

## Commands

- `uv run companion memory review`: asks every question until none are left or you quit. It is the `review` action of `companion memory`, declared in `cli/memory.py`.

## Measured

Nothing yet.

## Tests

`tests/features/upkeep/review/`
