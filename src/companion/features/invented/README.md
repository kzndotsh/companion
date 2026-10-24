# Invented (G42, J9)

Measures how often a reply states something about the person that neither the conversation nor its memory supports. It is a measurement, never on the reply path.

**Status:** measurement only. No switch. Runs only from `companion invented`.

## How it works

`check_new` in `run.py` judges recent replies, oldest first, until a spend cap is reached. Each turn is judged once.
- A turn counts when it was said for real (not in a pretend scene) in the last `--days`, has a recorded request with its memory card, and has no check yet.
- The judge `system/invented-judge` gets the 40 messages before the reply, their message included (`RECENT` in `store.py`, what the talker saw), the memory lines from the card (`memories_from_card`), and the reply. It lists each statement in the reply that asserts a fact about their own life, with the exact words and what supports it: `conversation`, `memory` or `none`.
- Code keeps only statements whose quote is really in the reply, is said to them (it contains you, your, you're and so on), and has a known support. Anything else is dropped. An answer of the wrong shape skips the turn without recording it.
- A failed call skips the turn and it is left for next time. The run checks the spend before each turn and stops at the cap with a log line. Spend is tagged `invented`.
- Each verdict is stored once per turn in `invented_checks`, with the judge's model and the prompt as `name@version`, append-only.

**The rate.** `report` in `logic.py` prints how many replies were checked, how many said something about them, and how many have a statement with support `none`, plus up to 8 examples. These are candidates, not the rate: on real replies the cheap judge was right about one time in twelve, since most flags were questions, reactions, compliments or the companion's own wishes. The rate is what a stronger reader confirms from `--dump`, which writes each flagged reply with the messages before it, its card and the quotes. That review is a Claude judge run by hand, not code.

## Files

| File | What |
|---|---|
| `logic.py` | pure: the judge's prompt and schema (`PROMPT`, `SCHEMA`), `build_prompt`, `parse` (which statements count), `invented`, `report` |
| `run.py` | effects: judging new replies within a spend cap, each turn once (`check_new`) |
| `store.py` | its queries: `invented_checks` (tables in `store/sqlite/migrations/0025_invented_checks.sql`), `RECENT` |
| `cli.py` | `companion invented`: judge recent replies within a cap, then print the report (`judge_now`) |

## Prompts

- `system/invented-judge`: lists statements about the person's life and what supports each. A failed call skips the turn, and a malformed answer is not recorded.

## Commands

- `uv run companion invented --days 7 --cap 0.2 --dump out.json`: judges new replies from the last 7 days (default 7) up to a spend cap in dollars (default 0.10), prints the report, and with `--dump` writes the candidates with their context to a file.

## Measured

- 2026-10-20: on 367 replies over two days ($0.09), the first prompt flagged 83 and the tighter prompt with the "said to them" rule flagged 63. A Claude judge found 6 invented statements in 5 replies, about 1.4% of replies, 12 supported by older messages and 49 not claims, so the cheap judge is right about one time in twelve (`evals/CHANGELOG.md`).

## Tests

`tests/features/invented/`
