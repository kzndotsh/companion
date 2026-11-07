# Agent guide

Read this first. `CLAUDE.md` is a symlink to this file, so every agent sees the same rules.

## What this is

A Telegram (or Discord, `COMPANION_PLATFORM`) companion bot that tries to be the most human-like AI
companion, plus the memory engine under it. One person talks to it, marks a reply `/flag` when it feels off and `/fav` when it
delights, and those marks set priorities. It runs from `src/companion`. It is a single-user
project: the bot runs on the owner's machine, and the repo is pushed to a GitHub remote (`origin`).

## Where things live

| Where | What |
|---|---|
| `GLOSSARY.md` | the project's words, one meaning each, with the ones to avoid and the words that mean more than one thing |
| `docs/user/features.md` | every feature in plain words, with its status: the user's guide |
| GitHub issues on `kzndotsh/companion` | the work: one issue per item, labelled by state (`docs/agents/triage-labels.md`). The pinned Plan issue (#183) is the order: Now, Next, Later and the decisions waiting on the owner (`needs-info`). Pull work from there. The repo is public, so issues are too |
| `src/companion/features/<name>/README.md` | how each feature works, with its files and setting: read it before changing the feature |
| `docs/dev/turn.md`, `docs/dev/delivery.md`, `docs/dev/initiative.md`, `docs/dev/memory.md` | how the reply path, delivery on Telegram and Discord, plans and reach-outs, and memory over time work, for what is not a feature folder |
| `docs/adr/` | decisions, once made, with the reason |
| `docs/research/` | audits and studies. Read-only background. Local only: git-ignored, not committed |
| `src/companion/prompts/` | every prompt the bot sends, as versioned text: `system/` (the persona and the judges' prompts), `notes/` (lines added to the talker's system block each turn), `messages/`. `README.md` lists them, `manifest.toml` says which version is current |
| `src/companion/prompts/CHANGELOG.md` | every version of every prompt and every change to how a request is assembled, with the reason |
| `docs/dev/evals.md` | how we measure: fixtures, samples, variants, replays, blind Claude reviewers, costs, reading a result; what the record shows, and the numbers behind today's choices (add a row when a measurement changes one) |
| `evals/README.md`, `evals/CHANGELOG.md` | how the eval runner works, and what it has measured |
| `evals/fixtures/` | public scripted fixtures. `evals/local/` is private, not committed |

## Commands

```bash
just check        # lint, types, import layers, tests. Run before every commit
just run          # start the bot (uv run companion run)
just logs         # follow data/logs/companion.log: every stage, judge, model and Telegram or Discord call
just restart      # stop the running bot, wait for it to exit, start the new one here
just commit "feat(x): msg" path...   # commit only the named files; refuses dirs, secrets, attribution
just inbox some idea   # jot an idea as a GitHub issue labelled needs-triage
uv run companion flags | favorites | spend | beliefs | initiative | prompts | mood | address | map | backup | calendar | shadows | crisis | now | intimate
uv run companion memory review | group   # questions for the owner (conflicts, new boundaries), merge proposals
uv run companion promises | lore | history   # shadow lists, its own tastes and its own past
uv run companion retire ID --reason "..." | merge ID ID --claim "..."   # close one memory, or merge by hand
uv run companion reminders [--cancel ID]   # the reminders they asked for and what became of each
uv run companion audit callbacks | invented --days 7 --cap 0.2 --dump F.json   # callbacks to memories; made-up facts candidates, confirm with a Claude reviewer
uv run companion replay <turn_id> [--show-prompt]   # rebuild a turn; --show-prompt prints everything it sent
uv run companion eval --variants v41.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

Strict ruff and basedpyright, a lefthook pre-commit, and import-linter run on every commit. Layer
rules: `core` imports nothing from the shell, only `store`, `lib/sqlite` and a feature's `store.py` import
`sqlite3`, and `lib` imports nothing from the companion. `core` may import
`companion.prompts`, which only reads packaged text. Imports point down (`direction` contract):
`turn/` (the reply path's stages) and `memory/` (the memory pass, nightly, rebuild, views) run features, so
they sit above `registry.py` and `features/`; what a feature uses sits below in `kit/` (the turn's
values and `Runtime`, `Feature`, `ask`, `reads`, `record`, `curate`, `embed`, `beside`), then `core/`
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
- **Not doing:** forking or depending on any audited project (none is a base we would trust); hand
  approval as the end-user product (it stays an override only); a model that has to be told not to
  recite (fix where the data sits instead); more models for their own sake (a model is tested when a
  flag or a measurement points at a gap).

## What runs in shadow

A feature in shadow works out and logs what it would do, and changes nothing in the chat. Each has a
review date, and at its review it goes live or is removed. `uv run companion shadows` is the source
of truth (from `core/shadows.py`, overdue first); this table is a snapshot of it, so update both
together.

| Feature | Setting | Read it with | Review by |
|---|---|---|---|
| Reaching out first about a due plan | `COMPANION_INITIATIVE` | `companion initiative` | 2026-11-24 |
| One light nudge after they stepped away ("shower time") and stayed gone much longer | `COMPANION_INITIATIVE` | `companion initiative` | 2026-11-24 |
| Reaching out for its own reasons: a thought, a time they keep, missing them (ADR 0021), at the share `COMPANION_REACH` sets | `COMPANION_INITIATIVE` | `companion initiative` | 2026-11-10 |
| The promises it made in its own replies, and each reply checked against them (J12) | `COMPANION_PROMISES` | `companion promises`, the decision log | 2026-11-17 |
| How often it brings a thread up, learned from how they met the last ones (ADR 0023) | always shadow for now | the decision log | 2026-11-08 |
| What they said is coming, kept until it happens, and the note that says so (ADR 0024) | `COMPANION_NOW` | `companion now` | 2026-11-08 |
| Its own history: stories of its past it made up in chat, checked against the sheet and kept as canon, and the ones it would show (ADR 0025) | `COMPANION_HISTORY` | `companion history`, the decision log | 2026-11-09 |

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
- Persona text and public fixtures are general. Nothing in them is about one person. Recorded turns
  live in `evals/local/`. Issues and docs stay generic and self-contained: issues are public.
- A line for the system block is a note source, named in `ORDER` in `turn/notes.py` in the order it is sent:
  it reads the turn (`Moment`) and what earlier sources offered, and returns its lines plus any writes that
  use up a limit or mark a plan asked, which run only once the turn is stored. Add a note there, not in
  `assemble`. A feature's note is its `Feature.note`; a note that is not a feature's goes in `_LOCAL`. A note
  that asks them something says so on its offer (`Offer(asks=True)`, read by `asking` in
  `kit/features.py`), so the question-run note and the calendar stay out that turn. A note that reads an
  earlier note by name declares it (`Feature.reads`, `_LOCAL_READS`), checked at load against `ORDER`. A reply that
  came back empty runs none of the notes' writes. The look-ups a note reads (`look`) run side by side under one 9 s deadline; a late or
  failed one adds nothing that turn. A feature's shadow look-up is its `Feature.shadow`; `turn/beside.py` runs each beside the turn and logs a failure.
- A turn runs in stages, one module each: `turn/listen.py` (a reaction instead of a reply, the listening
  read), `turn/route.py` (which talker), `turn/notes.py` `look` (the look-ups), `turn/assemble.py` (the
  request), `turn/crisis.py` (a risk read sets a scene aside and adds the fixed crisis-line message),
  `turn/reactions.py` (the reaction judges, run by listen, talk and persist),
  `turn/talk.py` (the talker), `turn/gate.py` (the reply gate: the checks before a reply is sent, their order and redraws; the checks themselves are in `core/reply_gate.py`), `turn/beside.py` (shadow tasks) and
  `turn/persist.py` (their message kept once, the reply stored). `turn/fast.py` is only the driver (`handle(runtime, ...)`;
  the `Runtime` it runs with is plain data in `kit/runtime.py`, built only by `compose.runtime` from `Settings`, so it has no switch defaults of its own; tests get one from `tests/runtime.py`): change a stage in its module.
- A feature declares its parts as a `Feature` in its own module (`kit/features.py`): a look-up before the
  reply, a note, steps after a memory pass, a look-up in shadow beside the turn, and a step once the
  turn is stored (`after_turn`, with their message and the reply). It is one line in `FEATURES` (`companion/registry.py`); a note
  also goes by name in `ORDER` in `turn/notes.py`, which is checked when the module loads. No field on
  `Lookups`, no branch in `look`. Its look-up runs with the others under the deadline, and what it found
  reaches its note as its argument; a stage that cannot name the feature asks `Lookups.find(Type)`. A
  feature that changes the request's card declares a `lane` (`Feature.lane`, `kit/features.py`). A stage
  never imports a feature: what the turn owns itself (reactions, the crisis path's scene rule, method
  check and fixed message) lives in `turn/` and `core/`. A feature that would bring something up on its
  own declares a `mention` (its best candidate, `core/turn/mentions.py` `MentionCandidate`), not a note:
  one picker (`turn/mention.py`) gates, ranks, counts one a day and logs it, and a new mentioning feature
  names its decision key in `MENTION_KEYS` in `core/turn/mentions.py` (checked when the picker loads). `FEATURES` in `registry.py` is the list of what is
  registered, in the order the after-steps run.
- Each feature lives in one folder under `src/companion/features/`: `logic.py`
  (pure), `run.py` (effects and its `Feature`), `store.py` (its queries, as a class bound to the
  connection), `cli.py`, `README.md` (how it works). A group of close features (`upkeep/`, `curiosity/`, `flow/`, `diction/`) holds one such folder per part and a README naming them;
  its parts may import each other. import-linter keeps a feature's logic pure, keeps features from importing
  each other, and lets only a feature's `store.py` touch sqlite. Prompts and migrations stay central. Tests
  mirror the folder (`tests/features/<name>/`).
- A feature owns its tables. Its `store.py` holds one class built from the connection (`Stories`,
  `Threads`), and the feature reaches it with `store.part(Threads)` on the `Store`
  (`store/sqlite/store.py`), which names no feature: it is the connection, the ledger and the tables
  the whole system reads (utterances, beliefs, decisions, turns, flags, favorites, spend, labels,
  embeddings, settings, sent and received messages, the reach-outs about a plan). A table one feature
  uses goes in that feature's `store.py`, never in `Store`. A feature that must read another
  feature's tables imports its store class and is named in the `features-are-independent`
  `ignore_imports` in `pyproject.toml`, with the reason; where a concept is read across the system,
  move it down to `store/sqlite/` instead. Every table is append-only by trigger or is named, with
  why, in `tests/store/test_append_only.py`.
- Ask a judge through `kit/ask.py`: declare it once, at module level, as a `Judge` (prompt, schema, parse, time limit, what a
  failed read means, whether a fallback model's answer counts, tries, and optionally a hedge: a second try started while a slow one still runs, first answer wins) and call `ask`, which returns a `Read`
  (value, model, cost, `name@version`) or None; `ask_or_raise` is for a step that fails as a whole (the memory pass). A judge's name is unique (`tests/kit/test_judge_names.py`): it is the log's name and the
  `COMPANION_JUDGE_ROUTES` key; its spend purpose is the name unless `spend` says another (the floor's three judges, the reach-out drafters and the name and pronoun captures each have a name and share one spend line). An answer
  only the caller can check (the labels it numbered) is parsed with `whole_answer` and finished by the caller; never build a `Judge` per call. Nothing calls `extract` outside `kit/ask.py` (a test checks it), and every
  call has a time limit.
- Ask a small model the same question several times with `kit/reads.py` `read_times` (each failed or
  unreadable read is None; one `attempt`, the call `ask` makes) and count agreement with `lib/vote.py` (`READS`, `unanimous`); a
  feature states what a failed read means for it (no agreement, or try the batch again later).
- Bound an embedding look-up with `kit/embed.py` (`embed_within` for one call, `bounded` for a look-up that embeds and more): it logs the failure with what it means and gives None. No new `asyncio.wait_for` around an `embed` call.
- Judges share one model (Haiku, DeepSeek on a refusal) unless `COMPANION_JUDGE_ROUTES` names the judge
  (by its `Judge` name or `read_times` `spend`); then it reads on that model first and Haiku second
  (`models/fallback.py` `ByJudge`; by default the crisis judge reads on DeepSeek). Route a judge there, never by choosing a model in a feature.
- Record a decision through `kit/record.py` (`Recorder.decide(key, detail, reason=...)`; in the turn,
  `decide(c, t, ...)` from `kit/current.py`), never by building `Decision(...)` by hand. Code that looks a past decision up
  matches its key (`decided_since`, `Decision.has_key`), never its reason text; decisions from before keys
  match by how their reason begins. Anything else a look-up needs to tell apart is a typed field in
  the detail (a belief closure's `mechanical`, a route's `talker` and `because`) or a field on the
  value (`Route.held`, `Route.brushed`), never a part of the reason. A key shared by readers is named
  once in one module (the reach-out keys are in `core/reachout.py`: `PLAN_HELD`, `OWN_HELD`,
  `PLAN_WOULD_SEND`, `OWN_WOULD_SEND`, `WOULD_NUDGE`); the stored strings never change. A loop event
  has a `key` column the same way (migration 0040).
- Some rules are tests (`tests/test_code_rules.py`): no matching a decision's reason text outside the
  allowed fallbacks for rows written before a key or field existed (listed there with the date each began), no file over 600 lines (a file listed in `CAPS` may be over it and may only shrink;
  none is listed today, and when one shrinks, lower its limit), and no more than 64 `noqa` comments in
  `src` (the limit; 60 today; a new one replaces an old one).
- Every feature in shadow has a row in `core/shadows.py` with a review date and what it is judged on
  (`companion shadows` lists them, overdue first); a test fails when a setting defaults to shadow without
  one. At its review it graduates or is removed, and its row goes.
- `tests/turn/test_chaos.py` runs whole turns against judges that fail, stall, answer from the fallback
  model or return junk at random (seeded): their message is stored once, a turn ends in a reply, a reaction
  or the floor's logged withholding, and a judge that always fails sends the talker what no judge would.
  Any change to the turn must keep it passing.
- Read the wall clock only through `core/clock.py` (`utc_now`, `local_zone`, a named zone with its rules). A test enforces it in `core/` and `kit/`
  (`tests/core/test_clock_guard.py`).
- A value or rule that must be the same in several places is named once and imported: in `core/` when
  several features use it, in the feature when only it does. The sensitivity cutoff is
  `core/sensitivity.py` `GUARDED_AT`, a heavy message is `HEAVY_AT` (`core/types.py`), the listening
  decision's key is `LISTENING_KEY` and its labels are read back through `logged_severity` (`core/turn/listening.py`),
  parts of the day are `core/daypart.py`, weekdays, months and a date in words are `core/dates.py`, a
  conversation's start is `core/rhythm.py` `first_of_each`, the memory pass's batch and context are
  `core/memory_pass.py`, the card's headings are in `core/card.py`, a fresh recorder or id is
  `kit/record.py`. A reason a person reads is rendered from the constant, never typed with its number.
  A table keyed by a kind names every kind (`tests/core/test_belief_kind_tables.py`).

**Evals**
- Every eval run has a spend cap, stated before the run. Check OpenRouter credits first. Keep
  experiments to cents.
- Do not act on fewer than about 12 samples per cell, and use 30 on a signal that matters. Two
  five-sample gaps in a row were noise. Say when a difference is within noise.
- A scripted fixture can pass where the recorded turn fails. Keep the recorded turn as a local fixture.
- A flag can be a rare draw. Replay the flagged turn 12 to 30 times and count before building a fix.
- Never quote a line you want in a prompt or note: the model copies it. Describe the behaviour. A
  note that only says "don't" seldom works; name the thing and give another way. The record behind
  these is "What the record shows" in `docs/dev/evals.md`.
- A judge or a grader is a model: check a few of its verdicts by eye. Use a different model from the one under
  test where you can.
- Scratch scripts for one-off experiments go in the session scratchpad, not the repo. Write the
  result and how to rerun it in `evals/CHANGELOG.md`.
- Evals run on the plain persona by default; the owner's character only as a labelled second check.

**Running the bot**
- Settings are environment variables in `.env`, listed with their defaults in `README.md`. They are read
  once into `companion/settings.py` (`Settings`, one row per switch in `SWITCHES`); the startup block
  (`startup_lines` in `daemon.py`: prompts, models, limits, then the switches as live, shadow, off and
  dials) is printed from it. A new switch is a named row there (`MOOD = Switch(...)`, listed in `SWITCHES`) and a field on `Runtime` set in `compose.runtime`; its uses name the row (`s.position(MOOD)`), never its label. `companion/compose.py` is the one place the models, spend sink and `Runtime` are built, for the bot, the one-off commands and the evals.
- The console shows INFO; `data/logs/companion.log` (rotating, not committed) keeps DEBUG with timings
  per stage and the full text of what was said. Secrets are scrubbed by value (`lib/logs.py`), and
  `httpx` stays at WARNING because its URLs carry the bot token.
- Never log or print a bot token. Telegram errors carry no URL (`TelegramError`), Discord errors only the
  call and its status (`DiscordError`).
- Restart with `just restart` in a terminal the owner can see, never as a hidden background job or under a
  timeout (it runs the bot in the foreground). It stops the old process first and waits while it answers
  what it already received (up to 30 s). Two bots on one token fight over updates. After a
  restart, confirm the startup block under "up as" shows the new prefix and persona.
- How a feature works is in its folder's `README.md`; the reply path, delivery, initiative and memory
  over time are in `docs/dev/turn.md`, `docs/dev/delivery.md`, `docs/dev/initiative.md` and
  `docs/dev/memory.md`. When you change one, change its description in the same commit.

**Working with the owner**
- Plain English, short, and say what changed and what it was measured on. Lead with what matters.
- "Wait" and "hold" mean do nothing yet. A question is not a request to build.
- Ask before spending beyond a cap, changing the live persona or model in a way that is not a
  reversible measurement, or deleting anything. Decisions the owner has parked stay parked.
- Never run filesystem-wide searches (`find /`, `grep -r` from `$HOME`). Scope to this repo.
- Subagents get the same rules in their brief, including the no-global-search rule, and they are
  read-only unless the task says otherwise.

## Agent skills

### Issue tracker

Work is tracked as GitHub issues on `kzndotsh/companion`, through `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default roles, each label named as its role. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root and `docs/adr/`. See `docs/agents/domain.md`.
