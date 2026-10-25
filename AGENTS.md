# Agent guide

Read this first. `CLAUDE.md` is a symlink to this file, so every agent sees the same rules.

## What this is

A Telegram companion bot that tries to be the most human-like AI companion, plus the memory engine
under it. One person talks to it, marks a reply `/flag` when it feels off and `/fav` when it
delights, and those marks set priorities. It runs from `src/companion`. It is a single-user,
project: the bot runs on the owner's machine, and the repo is pushed to a GitHub remote (`origin`).

## Where things live

| Where | What |
|---|---|
| `TODO.md` | the work board and the plan: where we are, measured facts, Now, Next and Later, the decisions waiting on the owner, then the cards (Doing, Waiting, Todo, Backlog with Parked, Done, Canceled). Pull work from here |
| `src/companion/features/<name>/README.md` | how each feature works, with its files and setting: read it before changing the feature |
| `docs/turn.md`, `docs/delivery.md`, `docs/initiative.md`, `docs/memory.md` | how the reply path, Telegram delivery, plans and reach-outs, and memory over time work, for what is not a feature folder |
| `docs/adr/` | decisions, once made, with the reason |
| `docs/inbox/` | ideas and questions that are not yet anything. Nothing there is a task |
| `docs/research/` | audits and studies. Read-only background. Local only: git-ignored, not committed |
| `src/companion/prompts/` | every prompt the bot sends, as versioned text: `system/` (the persona and the judges' prompts), `notes/` (lines added to the talker's system block each turn), `messages/`. `README.md` lists them, `manifest.toml` says which version is current |
| `src/companion/prompts/CHANGELOG.md` | every version of every prompt and every change to how a request is assembled, with the reason |
| `evals/README.md`, `evals/CHANGELOG.md` | how the eval runner works, and what it has measured |
| `evals/fixtures/` | public scripted fixtures. `evals/local/` is private, not committed |

## Commands

```bash
just check        # lint, types, import layers, tests. Run before every commit
just run          # start the bot (uv run companion run)
just logs         # follow data/logs/companion.log: every stage, judge, model and Telegram call
just restart      # stop the running bot, wait for it to exit, start the new one here
just commit "feat(x): msg" path...   # commit only the named files; refuses dirs, secrets, attribution
uv run companion flags | favorites | spend | beliefs | initiative | prompts | callbacks | mood | address | map | backup | calendar | shadows | crisis
uv run companion memory review | group   # questions for the owner, merge proposals
uv run companion promises | names | lore   # shadow lists and its own tastes
uv run companion reminders [--cancel ID]   # the reminders they asked for and what became of each
uv run companion invented --days 7 --cap 0.2 --dump F.json   # made-up facts candidates; confirm with a Claude judge
uv run companion replay <turn_id> [--show-prompt]   # rebuild a turn; --show-prompt prints everything it sent
uv run companion eval --variants v41.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

Strict ruff and basedpyright, a lefthook pre-commit, and import-linter run on every commit. Layer
rules: `core` imports nothing from the shell, only `store`, `lib/sqlite` and a feature's `store.py` import
`sqlite3`, and `lib` imports nothing from the companion. `core` may import
`companion.prompts`, which only reads packaged text. Imports point down (`direction` contract):
`turn/` (the reply path's stages) and `memory/` (slow loop, nightly, rebuild, views) run features, so
they sit above `registry.py` and `features/`; what a feature uses sits below in `loops/` (the turn's
values and `Conversation`, `Feature`, `ask`, `reads`, `record`, `curate`, `embed`), then `core/`
(shared vocabulary; `core/turn/` holds the reply path's own pure rules), then `lib/`.

## Principles

- **Rough first, then grow from real flags and measurements.** No feature without something that
  shows it is needed.
- **Every decision is logged with a reason written by code**, never by the model (ADR 0003, 0006).
- **Structural fixes beat prompt rules.** A prompt rule is a request and fails often. Encode a
  lesson as a test, a type or a check, not as more text.
- **Never rewrite what the model said.** Change what it sees, not what the user sees.
- **Nothing enters memory without a quote, a speaker and a frame** (ADR 0001, 0010). The ledger
  never deletes (ADR 0002): retire, close or mark, never remove.
- **Measure before switching** a model or a persona. Say what is measured and what is a guess.

## What runs in shadow

A feature in shadow works out and logs what it would do, and changes nothing in the chat. Each has a
review date, and at its review it goes live or is removed. `uv run companion shadows` is the source
of truth (from `core/shadows.py`, overdue first); this table is a snapshot of it, so update both
together.

| Feature | Setting | Read it with | Review by |
|---|---|---|---|
| Reaching out first about a due plan | `COMPANION_INITIATIVE` | `companion initiative` | 2026-10-31 |
| One light nudge after they stepped away ("shower time") and stayed gone much longer | `COMPANION_INITIATIVE` | `companion initiative` | 2026-10-31 |
| Reaching out for its own reasons: a thought, a time they keep, missing them (ADR 0021), at the share `COMPANION_REACH` sets | `COMPANION_INITIATIVE` | `companion initiative` | 2026-10-30 |
| What it would ask to get to know them | always shadow for now | `companion map` | 2026-10-26 |
| A light question when their words touch a basic it does not know (age, work, home, place, birthday, school) | always shadow for now | the decision log | 2026-10-26 |
| The nightly memory check and the write-time repeat check | `COMPANION_CONSOLIDATE` | `companion memory review` | 2026-10-26 |
| The mood (shadow by default; can be `on`) | `COMPANION_MOOD` | `companion mood` | 2026-10-26 |
| The promises it made in its own replies (J12) | `COMPANION_PROMISES` | `companion promises` | 2026-10-27 |
| Memories about a name they mention, left off the card | always shadow for now | `companion names` | 2026-10-27 |
| The crisis path: a second look at a message that may be a risk, and what each level would do (ADR 0022) | `COMPANION_CRISIS` | `companion crisis`, the decision log | 2026-11-01 |

## Rules we learned the hard way

**Git**
- Commit with `just commit "msg" file...`. It stages only the files you name and refuses directories,
  `.env`, `data/`, private `evals/` paths, attribution lines, and a commit when something else is
  already staged (after a `git mv`, add by name and use `git commit`). Never `git add -A`, `git add .`
  or `git add docs`: other sessions drop unread research files into the tree and they get committed by
  accident. Leave untracked files that are not yours alone.
- The shell is zsh, which does not split an unquoted variable into words. Pass file lists with arrays or
  `xargs`, and quote globs that may match nothing.
- Commit messages are a conventional prefix and a plain sentence. No attribution lines.
- Do not commit `.env`, `data/`, `evals/local/` or `evals/results/`.

**The prompt and what the model reads**
- The memory card, the clock and the notes go in the system block, never in the user's message. The clock
  and the notes are wrapped in `<clock>` and `<notes>` tags; the memory blocks stay bracketed text
  (`core/prompt/sections.py`, measured).
  Anything in the user's message can be read as something the user said, and it leaks into replies
  (ADR 0012). A note is chosen by code from a model's labels, never written by a model (ADR 0014).
- Every prompt is a versioned file under `src/companion/prompts/`. Never edit a shipped version: add the
  next `vN.md`, an entry in `prompts/CHANGELOG.md` and a line in `manifest.toml` (`tests/test_prompts.py`
  fails otherwise). A judge's or extractor's logged decision carries `name@version` (ADR 0013).
- Dropped and candidate persona versions stay as files. Each `vN.md` has a changelog entry and each
  entry has its file (`tests/test_persona_versions.py` fails otherwise). Never delete a version.
- A prompt change, or a code change that alters what the model is sent, goes in
  `src/companion/prompts/CHANGELOG.md`. Shipping a persona is changing `system/persona` in
  `manifest.toml`. A measurement goes in `evals/CHANGELOG.md`.
- Persona text and public fixtures are general. Nothing in them is about one person. Real turns
  live in `evals/local/`. Inbox notes and docs stay generic and self-contained.
- A line for the system block is a note source, named in `ORDER` in `turn/notes.py` in the order it is sent:
  it reads the turn (`Moment`) and what earlier sources offered, and returns its lines plus any writes that
  use up a cap or mark a plan asked, which run only once the turn is stored. Add a note there, not in
  `assemble`. A feature's note is its `Feature.note`; a note that is not a feature's goes in `_LOCAL`. A note
  that asks them something is named in `ASKING` (`loops/features.py`), so the question-run note stays out
  that turn. The look-ups a note reads (`look`) run side by side under one 9 s deadline; a late or
  failed one adds nothing that turn. A feature's shadow look-up is its `Feature.shadow`; `turn/beside.py` runs each beside the turn and logs a failure.
- A turn runs in stages, one module each: `turn/hear.py` (a reaction instead of a reply, the listening
  read), `turn/route.py` (which talker), `turn/notes.py` `look` (the look-ups), `turn/assemble.py` (the
  request), `turn/crisis.py` (a risk read sets a scene aside and adds the fixed crisis-line message),
  `turn/talk.py` (the talker and the reply checks), `turn/beside.py` (shadow tasks) and
  `turn/persist.py` (their message kept once, the reply stored). `turn/fast.py` is only the driver (`handle(convo, ...)`; the
  `Conversation` it runs is plain data in `loops/conversation.py`): change a stage in its module.
- A feature declares its parts as a `Feature` in its own module (`loops/features.py`): a look-up before the
  reply, a note, steps after a memory pass, a look-up in shadow beside the turn, and a step once the
  turn is stored (`after_turn`, with their message and the reply). It is one line in `FEATURES` (`companion/registry.py`); a note
  also goes by name in `ORDER` in `turn/notes.py`, which is checked when the module loads. No field on
  `Lookups`, no branch in `look`. Its look-up runs with the others under the deadline, and what it found
  reaches its note as `Lookups.found[name]`. Registered, in order: the memory map, the name and pronoun
  questions (basics), moves, mood, names, context, worth, relevance, recent times, topic-spent, guess,
  open loops, lore, own marks, reminders, the crisis path, nudges, the calendar and the basics hook.
- Each feature lives in one folder under `src/companion/features/`: `logic.py`
  (pure), `run.py` (effects and its `Feature`), `store.py` (its queries), `cli.py`, `README.md` (how it
  works). import-linter keeps a feature's logic pure, keeps features from importing each other, and lets only
  a feature's `store.py` touch sqlite. Prompts and migrations stay central. Tests mirror the folder
  (`tests/features/<name>/`). Move one with a script, never by hand, one feature per commit.
- Ask a judge through `loops/ask.py`: declare it once as a `Judge` (prompt, schema, parse, time limit, what a
  failed read means, whether a fallback model's answer counts, tries) and call `ask`, which returns a `Read`
  (value, model, cost, `name@version`) or None. No new `asyncio.wait_for` around an `extract` call.
- Ask a small model the same question several times with `loops/reads.py` `read_times` (each failed or
  unreadable read is None) and count agreement with `lib/vote.py` (`READS`, `unanimous`); a
  feature states what a failed read means for it (no agreement, or try the batch again later).
- Judges share one model (Haiku, DeepSeek on a refusal) unless `COMPANION_JUDGE_MODELS` names the judge
  (by its `Judge` name or `read_times` `spend`); then it reads on that model first and Haiku second
  (`models/fallback.py` `ByJudge`; by default the crisis judge reads on DeepSeek). Route a judge there, never by choosing a model in a feature.
- Record a decision through `loops/record.py` (`Recorder.decide(key, detail, reason=...)`; in the turn,
  `decide(c, t, ...)` from `loops/current.py`), never by building `Decision(...)` by hand. Code that looks a past decision up
  matches its key (`decided_since`, `Decision.has_key`), never its reason text; decisions from before keys
  match by how their reason begins.
- Some rules are tests (`tests/test_code_rules.py`): no matching a decision's reason text outside the three
  allowed fallbacks, no file over 600 lines (a file listed in `CAPS` may be over it and may only shrink;
  none is listed today, and when one shrinks, lower its cap), and no more than 64 `noqa` comments in
  `src` (today's count; a new one replaces an old one).
- Every feature in shadow has a row in `core/shadows.py` with a review date and what it is judged on
  (`companion shadows` lists them, overdue first); a test fails when a setting defaults to shadow without
  one. At its review it graduates or is removed, and its row goes.
- `tests/turn/test_chaos.py` runs whole turns against judges that fail, stall, answer from the fallback
  model or return junk at random (seeded): their message is stored once, a turn ends in a reply, a reaction
  or the floor's logged withholding, and a judge that always fails sends the talker what no judge would.
  Any change to the turn must keep it passing.
- Read the wall clock only through `core/clock.py` (`utc_now`, `local_zone`, `named_zone`). A test enforces it in `core/` and `loops/`
  (`tests/core/test_clock_guard.py`).

**Evals**
- Every eval run has a spend cap, stated before the run. Check OpenRouter credits first. Keep
  experiments to cents.
- Do not act on fewer than about 12 samples per cell, and use 30 on a signal that matters. Two
  five-sample gaps in a row were noise. Say when a difference is within noise.
- A scripted fixture can pass where the real turn fails. Keep the real turn as a local fixture.
- A judge is a model: check a few of its verdicts by eye. Use a different model from the one under
  test where you can.
- Scratch scripts for one-off experiments go in the session scratchpad, not the repo. Write the
  result and how to rerun it in `evals/CHANGELOG.md`.
- Evals run on the plain persona by default; the owner's character only as a labelled second check.

**Running the bot**
- Settings are environment variables in `.env`, listed with their defaults in `README.md`. They are read
  once into `companion/settings.py` (`Settings`, one row per switch in `SWITCHES`); the startup line is
  printed from it. A new switch is one row there.
- The console shows INFO; `data/logs/companion.log` (rotating, not committed) keeps DEBUG with timings
  per stage and the full text of what was said. Secrets are scrubbed by value (`lib/logs.py`), and
  `httpx` stays at WARNING because its URLs carry the bot token.
- Never log or print the Telegram token. Telegram errors carry no URL (`TelegramError`).
- Restart with `just restart` in a terminal the owner can see, never as a hidden background job or under a
  timeout (it runs the bot in the foreground). It stops the old process first and waits while it answers
  what it already received (up to 30 s). Two bots on one token fight over updates. After a
  restart, confirm the "up as" line shows the new prefix and persona.
- How a feature works is in its folder's `README.md`; the reply path, delivery, initiative and memory
  over time are in `docs/turn.md`, `docs/delivery.md`, `docs/initiative.md` and `docs/memory.md`. When you
  change one, change its description in the same commit.

**Working with the owner**
- Plain English, short, and say what changed and what it was measured on. Lead with what matters.
- "Wait" and "hold" mean do nothing yet. A question is not a request to build.
- Ask before spending beyond a cap, changing the live persona or model in a way that is not a
  reversible measurement, or deleting anything. Decisions the owner has parked stay parked.
- Never run filesystem-wide searches (`find /`, `grep -r` from `$HOME`). Scope to this repo.
- Subagents get the same rules in their brief, including the no-global-search rule, and they are
  read-only unless the task says otherwise.
