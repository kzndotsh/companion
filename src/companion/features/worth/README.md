# Worth

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |

Its prompts stay in `src/companion/prompts/`.

## How it works

Each new memory is labelled about their life, about the bot or one day's routine, keep cases first
(`system/memory-worth`, `features/worth/logic.py`): a remark about the bot is dropped, a routine is
closed a week on (at 04:00), and an unsure one is a question in `memory review`. `companion memory
context|label` backfill by hand.
