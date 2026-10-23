# Guess

| File | What |
|---|---|
| `logic.py` | pure: its rules, prompts' parsing and notes |
| `run.py` | effects: its `Feature` and what it does with the store and models |

Its prompts stay in `src/companion/prompts/`.

## How it works

When a short question of theirs invites a guess about them ("you know what time it is?"), its own
judge says so, the recall look-up picks what may fit (never sensitive), and one note asks for a
single playful guess as a question (`features/guess/logic.py`, J16). A hint at what it is time for
is looked up as a habit or routine of theirs (`system/guess-invite` v2), never as the clock. It
never guesses unasked.
