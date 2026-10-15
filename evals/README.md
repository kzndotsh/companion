# Evals

Replay a recorded turn against a persona variant, score the reply, and print one table.

```bash
uv run companion eval --list                         # the fixtures
uv run companion eval --variants v9.md,v10.md --dry-run   # the plan and its estimated cost
uv run companion eval --variants v9.md,v10.md --samples 3 --cap 0.20 --show
```

## How it works

- A **fixture** is a JSON file with a description and checks, and either:
  - a `script`: a short invented conversation (history, the user's last message, an optional memory
    block). It needs nothing else, so **anyone can run it.** The public fixtures in
    `evals/fixtures/` are all scripts, written to be neutral and to cover a failure *class*, not
    one person's conversation.
  - a `turn`: an id of a turn in your local database, replayed exactly. These hold only an opaque id
    and a generic description, never the conversation, and need your database. They live in
    `evals/local/`, which is **gitignored**, and are for private regression checks on your own
    real conversations. Their ids end in `-local` so the two sets never mix up in a table.
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

For a general failure class, write a script in `evals/fixtures/` with an invented conversation. To
capture something from real use, flag the turn with `/flag`, find its id (`uv run companion flags`),
and add a JSON file in `evals/local/`. Prefer writing the script version too, so the finding is
reproducible by others. Write the
criterion so that a stranger could grade a reply from it alone.

## Results log

Measured findings, newest last. Each line says what was run so it can be rerun.

- **2026-10-15. The memory block does not measurably hurt following the last message.** Persona
  v10, 12 samples per cell, with and without the block (`--variants v10.md,v10.md+nocard`).
  `answers-the-question-just-asked`: 12/12 both. `agree-and-invent`: 6/12 with, 7/12 without.
  An earlier 5-sample run had shown 3/5 against 5/5 on the first fixture, and that gap was noise.
  The turn that was flagged in real use was a rare failure (about 1 in 17 across all samples).
- **2026-10-15. v9 and v10 are not distinguishable** on `agree-and-invent`,
  `play-invitation` and `signoff-then-time-skip` at 7 samples per cell. See
  `src/companion/persona/CHANGELOG.md`.
- **2026-10-15. The judge agreed with a human reading on 23 of 24** judged replies in the first
  run. This was a spot check by the author, not independent labelling.
- **Lesson on small samples.** Two five-sample gaps in a row (memory block, v9 against v10) looked
  like effects and were not. Do not act on fewer than about 12 samples per cell.
