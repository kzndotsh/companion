# Topics

Moves the chat on when a small topic has run its course, instead of asking about smaller and smaller details of the same thing. It came from a flag on a chat that narrowed to a minor detail.

**Status:** live. No switch. It runs before the reply, and its note goes in the system block.

## How it works

A topic kept alive only by minimal replies is withering, and people end it by starting a new one, usually linked to the old. Its own judge labels the moment. The listening judge is not used, so the age floor it carries stays as it was.

The judge is asked only on a likely moment. The turn must be casual (read as not serious, real frame, not a goodbye), their message at most 5 words with no question mark, and the companion's last reply must have asked something. Other turns make no call. The judge (`system/topic-spent`, 3 s limit) sees the last 8 messages and says whether the topic is spent. A failed or unreadable answer means no note, and a fallback model's answer is not trusted.

Code then decides whether to act. No note comes if their message has a question mark. The note is sent only on a quiet turn: casual, no name being asked, no check-in and nothing held. It is sent at most once in 10 of their messages, checked against the logged decisions of their last 9 earlier turns.

The move it names is chosen by code. If a plan of theirs was offered as a note this turn, it moves on to that (`notes/topic-move-loop`). Otherwise by their local hour: day from 5 (`notes/topic-move-day`), evening from 17 (`notes/topic-move-evening`), and from 22 until 5 a thought of its own rather than another question (`notes/topic-move-night`). `notes/topic-spent` wraps the move. It sits after the plan note and before guess.

The decision is logged once the reply is stored, under the key `topic: run its course, moving on`, with the move and note versions.

A move to their day, their evening or a plan of theirs asks them something, so its offer says `asks` and the question-run note stays out that turn; the late-night move shares something of its own and does not (`asks` in `logic.py`).

## Files

| File | What |
|---|---|
| `logic.py` | pure: the likely-moment gate, the judge prompt, parsing, which move to name, the note, the limits |
| `run.py` | effects: the judge (`SPENT`), the look-up, the once-in-10 check, logging, and the `Feature` (`TOPICS`) |

## Prompts

- `system/topic-spent`: says whether the topic has run its course. Unreadable or late means no note.
- `notes/topic-spent`: react briefly and move on, with the chosen move.
- `notes/topic-move-loop`: move on to a plan of theirs.
- `notes/topic-move-day`: move on to their day.
- `notes/topic-move-evening`: move on to their evening.
- `notes/topic-move-night`: late at night, a thought of its own.

## Commands

None.

## Measured

- 2026-10-19: the judge was 30/30 on 10 invented chats. In the afternoon the note moved the chat on 30/30 against 1/30 without. Late at night a thought of its own came 18/30, and the first night wording invented things it did, 21/30 with a character, against 0/30 for the second. About $0.12 (`evals/CHANGELOG.md`).
- 2026-10-21: a v2 note ("keep the conversation going") kept the chat going 8/30 against 6/30 for v1, within noise. Dropped (`evals/CHANGELOG.md`).
- 2026-10-25: judge bake-off on the live topic-spent suite (30 cases): Haiku 30, GPT-6 Luna 29, DeepSeek 27. DeepSeek read a first mention of a food as a spent topic. Haiku stays the judge (`evals/CHANGELOG.md`).

## Tests

`tests/features/topics/`
