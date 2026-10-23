# Hooks (J48)

When their own words touch a basic fact about them without giving it, log whether it would ask.
Shadow only: nothing reaches the talker.

| File | What |
|---|---|
| `logic.py` | pure: the basics, reading which one a message touches, when it may ask |
| `run.py` | effects: the reads beside the turn (`HOOKS`) and the check of memory |

Its prompts stay in `src/companion/prompts/` (`system/basics-hook`, `system/basics-known`).

## How it works

On a casual turn, when their message touches a basic fact without giving it (age, work, who they
live with, where they live; three agreeing reads of `system/basics-hook`, 5 s each), code checks
memory with `system/basics-known` (5 s) and, at most once a day and twice per basic, logs whether it
would ask or memory already knew. A failed or slow read means no pick that turn.
