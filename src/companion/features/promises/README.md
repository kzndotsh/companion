# Promises (J12)

Records the promises the companion makes in its own replies, such as a promise to stop using a word. A repair promise lived only in the messages in view, and the companion broke one a few hours after making it.

**Status:** shadow (review by 2026-10-30, judged on whether standing promises are worth pinning, J12 step 2 and LR5). `COMPANION_PROMISES`: `shadow` (default, records and lists), `off` (skips it). Runs after a memory pass, inside the open-loop batch. Nothing reaches the talker.

## How it works

**Where it runs.** The memory pass hands `read_promises` to the open-loop pass (`Reading` in `features/threads/run.py`) when the switch is not `off`. The open-loop pass reads its own bookmark in batches of 40 messages with 4 before them as context, up to 3 batches per call. Their messages go to the open-loop reader as before and the companion's messages in the same batch go to the promise reader. Both must succeed for the batch to count as read.

**The read.** `system/promise-read` gets the batch with the companion's messages as targets and returns, for each promise, the message label, the exact quote, a one-sentence claim, a kind (`standing`: a rule for every later message, `once`: one thing on a later day) and `avoid`, a word it promised to stop using or an empty string. Most messages contain none. The prompt counts only a promise to change how it talks or acts from now on, made because they asked, corrected it or complained. Limits, banter, company, reassurance, apologies with no rule and anything in a scene are not promises.

**What code keeps** (`to_promise` in `logic.py`). A proposal is dropped, with the reason logged as "promise dropped: ...", unless all of these hold:
- the message is one of its own, and the quote is in that message's text;
- the message was said for real, not in a pretend scene;
- the quote is not hedged (try, should, might, maybe, hope, probably, could);
- the quote looks forward (won't, I'll, we'll, no more, stop, from now on, next time, again, always, never, anymore);
- the kind is known;
- a word to avoid is at most 3 words and appears in the promise's message or the 3 before it (`NEAR`).

A promise already recorded for the same message and quote is not stored twice. Each new one is stored in `promises` with its model and prompt as `name@version`, and the decision "promise recorded from its own words (shadow)" is logged with the kind, claim, quote and avoid word.

**Failures.** A failed call returns None, so the batch is not marked read and is tried again next pass. After 3 failed tries on one batch (`MAX_TRIES` in the open-loop pass) it is let go, with the reason logged, so plans never wait on it. A malformed answer is logged as "promises: the answer was malformed and was ignored" and counts as read. Spend is tagged `promises`.

**The owner's marks.** `companion promises` lists the current ones, newest first, at most 30. `--not ID` marks one as not a promise and `--retire ID` retires it. Marks are appended with the reason "the owner said so", never deleted, and a marked promise leaves the list. The ID is a prefix and must match exactly one current promise.

It never shows a promise to the talker and never enforces one.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the prompt, the schema, `parse`, and `to_promise` (which promises code keeps), the `Promise` type and its `Kind` |
| `run.py` | effects: reading its own messages in a batch (`read_promises`) |
| `store.py` | its queries: `promises` and `promise_marks`, append-only (tables in `store/sqlite/migrations/0022_promises.sql`) |
| `cli.py` | `companion promises`, `--not`, `--retire` (`run`) |

## Prompts

- `system/promise-read`: finds the promises in its own messages. A failed call keeps the batch for another try and a malformed answer is ignored.

## Commands

- `uv run companion promises`: the promises it made, newest first.
- `uv run companion promises --not ID`: marks one as not a promise.
- `uv run companion promises --retire ID`: retires one.

## Measured

- 2026-10-20: on all 1,040 of its messages, a first prompt kept 101 with about 12 real, a tighter prompt kept 32 with about 11 real, and a code check that the quote looks forward left 15 with 11 real, losing none that the tighter prompt had found. One real promise was missed (`evals/CHANGELOG.md`).

## Tests

`tests/features/promises/`
