# Topics

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |

Its prompts stay in `src/companion/prompts/`.

## How it works

When a small topic has run its course (a short answer right after it asked something, read by its
own judge `system/topic-spent`, never the listening judge), one note says to react briefly and move
on (`features/topics/logic.py`): to a plan of theirs offered that turn, else their day or evening,
and late at night a thought of its own. At most once in ten of their messages, casual turns only,
never past a question.
