# Promises (J12)

The promises the companion makes in its own replies. Shadow only: recorded and listed, never shown
to the talker yet (`COMPANION_PROMISES`, `off` to skip).

| File | What |
|---|---|
| `logic.py` | pure: the prompt, parsing, and which promises are kept |
| `run.py` | effects: reading its own messages in a batch (`read_promises`) |
| `store.py` | its queries (the tables are in `store/sqlite/migrations/0022_promises.sql`) |
| `cli.py` | `companion promises`, `--wrong`, `--retire` |

Its prompt stays in `src/companion/prompts/` (`system/promise-read`).

## How it works

Its own messages are read in the open-loop batch, sharing that batch's bookmark: the slow loop
hands `read_promises` to the batch when the setting is on, and a failed read keeps the batch for
another try. A model labels each promise standing or once, and a word it said it would stop using;
code keeps one only if its quote is in that message, said for real, not hedged and forward looking.
