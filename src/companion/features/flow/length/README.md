# Length

The one word limit a reply gets, chosen by code from their message, never by a model (ADR 0014).

**Status:** live. No switch.

## How it works

On short, casual statements replies ran three to four times longer than the message they answered,
so a short statement is the only everyday case with a target. A statement of at most 12 words with
no question gets about one and a half times its length plus 4, at least 8 words, scaled by 0.6 to
1.5 per turn, seeded by the turn so a replay rebuilds the same note (`notes/length`). A message the
listening judge reads as serious gets a fixed 35 words (`notes/length-serious`).

No limit on an acute message, in a scene, on a question (with or without a question mark, "what
about you" included), or on a turn the crisis path reads as a risk. A short "i want to die" is never
answered under a word cap.

The note goes in the system block right after the scene note. Each turn logs a `length` decision
with the limit and the reason code wrote, or "no cap".

## Files

| File | What |
|---|---|
| `logic.py` | pure: when a message gets a target, its size, the variation, the note |
| `run.py` | the note as a `Feature` (`LENGTH`), and the logged decision |

## Prompts

- `notes/length`: a short statement, under about `$limit` words.
- `notes/length-serious`: a message read as serious, under about 35 words.

## Commands

None. `companion replay` shows the note a turn got.

## Measured

- 2026-10-23, 370 real turns: limits ran 5 to 20 words, but replies sat near 15 to 20 whatever the
  limit, and about two thirds went over it (TODO T16).

## Tests

`tests/features/flow/length/`
