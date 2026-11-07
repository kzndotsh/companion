# Promises (J12)

Records the promises the companion makes in its own replies, such as a promise to stop using a word. A repair promise lived only in the messages in view, and the companion broke one a few hours after making it.

**Status:** shadow (review by 2026-11-17, judged on would-redraws that read as real breaks, none on a reply that kept them, and breaks the owner flags with `forgot` that the check also caught; the first review, 2026-11-03, found 22 promises in two weeks, about 8 concrete, most already pinned as memories of kind `promise`). `COMPANION_PROMISES`: `shadow` (default, records and lists), `off` (skips it). Runs after a memory pass, inside the open-loop batch. Nothing reaches the talker.

## How it works

**Where it runs.** The memory pass hands `read_promises` to the open-loop pass (`Reading` in `features/threads/run.py`) when the switch is not `off`. The open-loop pass reads its own bookmark in batches of 40 messages with 4 before them as context, up to 3 batches per call. Their messages go to the open-loop reader as before and the companion's messages in the same batch go to the promise reader. Both must succeed for the batch to count as read.

**The read.** `system/promise-read` gets the batch with the companion's messages as targets and returns, for each promise, the message label, the exact quote, a one-sentence claim, a kind (`standing`: a rule for every later message, `once`: one thing on a later day) `avoid`, a word it promised to stop using or an empty string, and `checkable`, whether a later reply could keep or break it. Most messages contain none. The prompt counts only a promise to change how it talks or acts from now on, made because they asked, corrected it or complained. Limits, banter, teasing, a joke shaped like a promise, compliments, company, reassurance, apologies with no rule and anything said in a scene are not promises; a sincere promise about how it handles scenes, said outside one, is.

**Three reads.** Each batch is read three times at once (`read_times`); a failed or unreadable read keeps the batch for another try. A promise counts only when all three reads found it (the same message, quotes that overlap) and is checkable only when all three said so (`agreed` in `logic.py`); one found by only some reads is logged as "promise dropped: the reads did not agree". Asked once, the reader took jokes and compliments said in ordinary chat for promises (review of 2026-11-03).

**What code keeps** (`to_promise` in `logic.py`). A proposal is dropped, with the reason logged as "promise dropped: ...", unless all of these hold:
- the message is one of its own, and the quote is in that message's text;
- the message was said for real, not in a pretend scene;
- the quote is not hedged (try, should, might, maybe, hope, probably, could);
- the quote looks forward (won't, I'll, we'll, no more, stop, from now on, next time, again, always, never, anymore);
- the kind is known;
- it is checkable: it names something a later reply could keep or break, or it has a word to avoid;

**How long it lasts.** Each kept promise has a scope: `lasting` (how it treats them or talks to them, until they release it) or `moment` (one joke, one slip or one moment). It is a moment's only when all three reads said so. A moment's promise binds for a week (`MOMENT_DAYS`, `in_force`), as a one-day moment leaves the card after a week: a promise to retire a joke about one mishap outlived the mishap (review of 2026-11-03). The scope is stored in `promise_scopes`, append-only, the newest row winning; a promise with none is lasting. The check on each reply reads only promises in force.

The list:
- a word to avoid is at most 3 words and appears in the promise's message or the 3 before it (`NEAR`).

A promise already recorded for the same message and quote is not stored twice. Each new one is stored in `promises` with its model and prompt as `name@version`, and the decision "promise recorded from its own words (shadow)" is logged with the kind, claim, quote and avoid word.

**Failures.** A failed call returns None, so the batch is not marked read and is tried again next pass. After 3 failed tries on one batch (`MAX_TRIES` in the open-loop pass) it is let go, with the reason logged, so plans never wait on it. A malformed answer is logged as "promises: the answer was malformed and was ignored" and counts as read. Spend is tagged `promises`.

**The owner's marks.** `companion promises` lists the current ones, newest first, at most 30, with their scope and whether a moment's has passed. `--not ID` marks one as not a promise and `--retire ID` retires it; `--moment ID` and `--lasting ID` relabel how long one lasts. Marks are appended with the reason "the owner said so", never deleted, and a marked promise leaves the list. The ID is a prefix and must match exactly one current promise.

**The check on each reply** (`check_reply`, the feature `promise check`, its `after_turn` step). Once a reply is stored, beside the turn so the next message never waits on it, a small judge (`system/promise-check`, 20 s, one try) reads the current promises (not marked by the owner), each under a label, the newest six messages and the reply. It names the promise the reply breaks in the way it meant it, or none, and the promises the newest messages show they released or that ran out. Not broken: they raised the thing or asked about it, released it, its time is over, keeping it would ignore a risk to their safety, it is too vague to break, or two promises pull apart. In shadow it logs `promise check (shadow): would redraw` with the promise, `promise check: kept`, and `promise check (shadow): would retire` for each one released; nothing is redrawn and nothing is marked. A failed or unreadable answer logs nothing. A code check on a promised word was tried first and got 13 of 32 edge cases, the judge 30 (`evals/CHANGELOG.md`, 2026-11-03), since a break is as often the same joke in other words as the word itself.

It never shows a promise to the talker and never enforces one.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the prompt, the schema, `parse`, and `to_promise` (which promises code keeps), the `Promise` type and its `Kind`; the check's input and answer (`check_input`, `read_check`, `Check`) |
| `run.py` | effects: reading its own messages in a batch (`read_promises`), and the check on each reply (`check_reply`, `PROMISE_CHECK`) |
| `store.py` | its queries as `Promises` (`Store.part(Promises)`): `promises`, `promise_marks` and `promise_scopes`, append-only (tables in `store/sqlite/migrations/0022_promises.sql` and `0039_promise_scopes.sql`) |
| `cli.py` | `companion promises`, `--not`, `--retire`, `--moment`, `--lasting` (`run`) |

## Prompts

- `system/promise-read`: finds the promises in its own messages. A failed call keeps the batch for another try and a malformed answer is ignored.
- `system/promise-check`: whether a reply breaks one of them, and which were released. A failed or unreadable answer logs nothing.

## Commands

- `uv run companion promises`: the promises it made, newest first.
- `uv run companion promises --not ID`: marks one as not a promise.
- `uv run companion promises --retire ID`: retires one.

## Measured

- 2026-10-20: on all 1,040 of its messages, a first prompt kept 101 with about 12 real, a tighter prompt kept 32 with about 11 real, and a code check that the quote looks forward left 15 with 11 real, losing none that the tighter prompt had found. One real promise was missed (`evals/CHANGELOG.md`).

## Tests

`tests/features/promises/`
