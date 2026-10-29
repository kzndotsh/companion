# Sort

It sorts each memory into about their life, a remark about the bot, or one routine moment. The memory pass had
kept remarks about the companion and one day's routine as lasting facts about them.

**Status:** live. No switch. It runs after each memory pass, once a night for routine expiry (with the 04:00 steps), and
from a command.

## How it works

The rule is the owner's: remarks about the bot are dropped, a routine moment lasts a week, and when it is
unclear the owner is asked.

Labelling. After each memory pass that stored new memories of theirs, up to 20 current memories not yet checked
(`limit`) are each read three times (`READS`) with the memory, its quote and the messages around it (6 before,
1 after). The prompt checks the keep cases first (how they want to be treated, feelings about the companion, building
it as part of their life, the habit behind a routine, a feeling or first or ongoing matter, anything they asked
to remember) and only then labels `about_the_bot`, `routine` or `keep`. Code takes the label all three reads
agree on. If they do not agree and any read said something other than keep, it is `unsure`. If every read
failed it is `keep`, so nothing is acted on.

Acting. A memory recorded within the last day is acted on. An agreed `about_the_bot` is retired at once, with the
reason "a remark about the bot, not their life (three reads agreed)". An agreed `routine` is stored as routine.
A memory kept earlier is never acted on: an agreed change is stored as a question instead (`ask_about_the_bot`
or `ask_routine`), and `unsure` is a question too. Questions appear in `companion memory review`. Every check is
stored with its three reads and the prompt version.

Expiry. Each night `memory/nightly.py` runs `expire_routine`. A current routine memory is retired with the reason
"a routine moment, a week on" once more than 7 days (`ROUTINE_DAYS`) have passed since it was last supported,
or since it began if it never was. Retiring closes a belief, never deletes it.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the labels, reading one, the verdict of three reads, a change turned into a question (`ROUTINE_DAYS`) |
| `run.py` | effects: labelling (`label`, `sort_new`), retiring, routine expiry (`expire_routine`), the `Feature` (`WORTH`) |
| `cli.py` | `companion memory label`: label every memory kept before the rule (`label_now`) |

## Prompts

- `system/memory-worth`: keep cases first, then about_the_bot, routine, keep or unsure. A failed read counts as no answer.

## Commands

- `uv run companion memory label`: labels every memory not yet checked (up to 1000), turns each change into a question, and prints the counts and cost. A model call.
- `uv run companion memory review`: answers the questions it leaves.

## Measured

- 2026-10-21: a first draft listing categories before exceptions dropped a third of what mattered, so the version checks keep cases first (`src/companion/prompts/CHANGELOG.md`, not in `evals/CHANGELOG.md`). Not otherwise measured yet.

## Tests

`tests/features/upkeep/sort/`
