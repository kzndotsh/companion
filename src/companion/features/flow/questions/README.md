# Questions

Two notes about questions, both after the history, outside a scene and not on a serious turn.

**Status:** live. No switch.

## How it works

**The run.** A question invites another: after one question reply about half the next ask again.
When each of its last three replies asked something (a `?`), the next reply gets `notes/question-run`:
ask nothing this time, but leave them something to answer. It stays out when another note asks them
something that turn (`asking` in `kit/features.py`).

**The game.** When one of their last three messages told it to ask them things ("ask me anything",
"quiz me"), with no pause over 10 minutes since and not called off, `notes/question-game` asks for
the next question after it answers or reacts. Its offer asks them something, so the run note stays
out. It also stays out on a turn the crisis path reads as a risk.

## Files

| File | What |
|---|---|
| `logic.py` | pure: whether a reply asked, the run, whether a game is on, the two notes |
| `run.py` | the notes as features: `GAME` and `QUESTIONS` |

## Prompts

- `notes/question-run`: ask nothing this time, but leave them something to answer.
- `notes/question-game`: after answering or reacting, ask them the next one.

## Commands

None.

## Measured

- 2026-10-24: a first wording that only said to ask nothing cut question replies from 14/30 to 1/30,
  but blind judges read its replies as dead ends; the shipped wording, which leaves them something to
  answer, is measured in `evals/CHANGELOG.md`.
- 2026-10-25: on two flagged game turns, 12 draws each, it asked the next question 12/12 and 12/12
  with the game note, 0/12 and 2/12 without.

## Tests

`tests/features/flow/questions/`
