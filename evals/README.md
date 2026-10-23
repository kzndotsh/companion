# Evals

Replay a recorded turn against a persona variant, score the reply, and print one table.

```bash
uv run companion eval --list                         # the fixtures
uv run companion eval --variants v40.md,v41.md --dry-run   # the plan, an upper estimate and the balance
uv run companion eval --variants v40.md,v41.md --samples 12 --cap 0.20 --show
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
- A **variant** is a persona version (`v41.md`, from `src/companion/prompts/system/persona/`) with optional
  flags, in any order, and `@model` last: `+nocard` drops the memory block, `+h10` keeps the last 10
  messages of history, `+low`, `+medium` or `+high` turns reasoning on, `+len` adds the length note and
  `+listen` adds the listening note the fixture's labels would produce, `+echo` the note against
  copying their emoji, `+as-NAME` lays a character sheet over the persona, `+mood-STATE` (or two joined
  with a dot) adds a mood line, `+resample` draws once more when the quip check fires, and `+roleplay`
  builds the roleplay talker's prompt (with `+as-NAME`, its sheet section too). `+tags` puts the whole
  system block in XML-style tags and `+tagsnotes` only the clock and the notes (as the bot does), and
  `+lore` shows a script's `lore` tastes as the companion's own (ADR 0020). The recorded history and the
  user's message are reused exactly, so only the thing under test changes. To try another version of a
  non-persona prompt, set `COMPANION_PROMPT_OVERRIDES` for the run.
- Free models for cross-model checks. `@kiro/claude-sonnet-4.6` (or another Kiro model) sends the talker
  request through the local Kiro gateway at `KIRO_GATEWAY_URL` (default `http://127.0.0.1:9000`) with
  `KIRO_GATEWAY_API_KEY` or `PROXY_API_KEY`; Kiro has no system role (the gateway pastes ours into the
  first user message) and adds a hidden coding-assistant prompt, so it is a rough second opinion, never
  a measurement of the live talker. `@<model>:free` uses OpenRouter's free models (20 a minute, 1,000 a
  day on this account; some are blocked by the account's privacy guardrail). Either kind runs one call
  at a time. Public fixtures only: real turns are not sent to these providers. Judging stays on the
  usual paid judge. Details, which models work and what the gateway changes: `evals/free-models.md`.
- Checks are either deterministic (`max_words`, `regex`, `not_regex`) or model-graded. `judge` answers
  `pass`, `fail` or `unclear` for one criterion; `epitome` scores a reply 0 to 2 on reaction,
  interpretation, exploration and support and passes with a reaction plus a strong interpretation, an
  exploration or support. A script (or a recorded turn) can carry `labels` (severity, stance, vague,
  medical) so `+listen` can add the matching note, and `lore` (a list of its own tastes) for `+lore`. `unclear` is unscored and never
  counts as a failure. The judge prompt and schema are hashed into every result.
- A sample passes only if every check passes. Cells read `passes/scored`, with `+k?` for unscored.
- **A spend cap is mandatory.** The runner adds up the cost each response reports and stops at the
  cap, saying so in the table. Before a run it shows the OpenRouter balance and refuses when the cap is
  above it, because the bot shares the credits. After a run it reads OpenRouter's meter again and
  prints what was charged; that figure covers the whole account, so a running bot adds to it.
  `--dry-run` prints the plan, an upper estimate and the balance, and spends nothing.
- **Bigger cards and longer history.** On a recorded turn, `+cardN` (or `+cardall`) rebuilds the card
  with N memories from the database as it stood at that turn, and `+histN` rebuilds the history with
  N earlier messages; the persona and the notes stay as recorded. They need `--db` and are ignored for
  scripted fixtures, which carry their own card.
- **Noise is in the table** (`lib/stats.py`). Each cell shows the 95% range the true pass rate probably
  sits in (Wilson; the textbook normal range is badly off at 12 to 30 samples). With two or more
  variants, each later one is compared with the first: per fixture by Fisher's exact test, adjusted for
  how many fixtures were compared (Holm), and in total by the Cochran-Mantel-Haenszel test, which
  compares within each fixture because samples of one fixture are alike. Under 5% chance of noise reads
  "a real difference"; anything else reads "within noise", with the samples per side a gap that size
  would need. Report a change as a gain only when it reads real.
- Results (every reply and every verdict) are saved to `evals/results/`, which is gitignored
  because it holds conversation text.

## Reading the numbers

- Three samples per cell is a smoke test, not evidence. Differences of one or two samples between
  variants are noise. Use `--samples 5` or more on the fixtures that matter before deciding.
- The judge is a model and can be wrong. On the first run it agreed with a human reading on 23 of
  24 judged replies. Read the replies (`--show`) for anything that decides a change.
- Fixtures marked as measuring "the talker alone" test the model without the live loop's other
  decisions, such as the acknowledgement route.

## Live tests

Opt-in tests call the real models, cost cents, and check that a judge agrees with a person on invented
examples: `uv run pytest -m live tests/live/test_ack_judge.py -s`, and likewise
`test_extraction_rules.py`, `test_listening_judge.py` and `test_empathy_judge.py`. They are skipped in
`just check` and CI.

## Adding a fixture

A fixture file is named after its id (`<id>.json`), and ids are unique across `evals/fixtures/` and
`evals/local/`; the loader refuses either mistake. `--fixture` takes the id, and an unknown one is an
error that names the closest id.


For a general failure class, write a script in `evals/fixtures/` with an invented conversation. To
capture something from real use, flag the turn with `/flag`, find its id (`uv run companion flags`),
and add a JSON file in `evals/local/`. Prefer writing the script version too, so the finding is
reproducible by others. Write the
criterion so that a stranger could grade a reply from it alone.

Retired local duplicates live in `evals/local/archive/`. The loader reads only the top level of each
fixtures directory, so archived files are kept but never run. Nothing in `evals/local/` is in git.

## Results log

Measured findings live in [CHANGELOG.md](CHANGELOG.md), newest last. Add a line there whenever
a run changes what we believe. Persona changes are logged in `src/companion/prompts/CHANGELOG.md`.
