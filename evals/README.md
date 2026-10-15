# Evals

Replay a recorded turn against a persona variant, score the reply, and print one table.

```bash
uv run companion eval --list                         # the fixtures
uv run companion eval --variants v9.md,v10.md --dry-run   # the plan and its estimated cost
uv run companion eval --variants v9.md,v10.md --samples 3 --cap 0.20 --show
```

## How it works

- A **fixture** (`evals/fixtures/*.json`) names a turn in the local database, says in plain words
  what a good reply does, and lists checks. It holds an opaque turn id and a generic description,
  never the conversation. The text stays in `data/`, so fixtures need your database to run.
- A **variant** is a persona file, optionally `+nocard` (drop the memory block) or `@model`. The
  recorded history and the user's message are reused exactly, so only the thing under test changes.
- Checks are either deterministic (`max_words`, `regex`, `not_regex`) or `judge`. A judge is a small
  model that answers `pass`, `fail` or `unclear` for one criterion. `unclear` is unscored and never
  counts as a failure. The judge prompt and schema are hashed into every result.
- A sample passes only if every check passes. Cells read `passes/scored`, with `+k?` for unscored.
- **A spend cap is mandatory.** The runner adds up the real cost each response reports and stops
  at the cap, saying so in the table. Always run `--dry-run` first.
- Results (every reply and every verdict) are saved to `evals/results/`, which is gitignored
  because it holds conversation text.

## Reading the numbers

- Three samples per cell is a smoke test, not evidence. Differences of one or two samples between
  variants are noise. Use `--samples 5` or more on the fixtures that matter before deciding.
- The judge is a model and can be wrong. On the first run it agreed with a human reading on 23 of
  24 judged replies. Read the replies (`--show`) for anything that decides a change.
- Fixtures marked as measuring "the talker alone" test the model without the live loop's other
  decisions, such as the acknowledgement route.

## Adding a fixture

Flag the turn with `/flag`, find its id (`uv run companion flags`), and add a JSON file. Write the
criterion so that a stranger could grade a reply from it alone.
