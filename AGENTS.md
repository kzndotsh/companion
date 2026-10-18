# Agent guide

Read this first. `CLAUDE.md` is a symlink to this file, so every agent sees the same rules.

## What this is

A Telegram companion bot that tries to be the most human-like AI companion, plus the memory engine
under it. One person talks to it, marks a reply `/flag` when it feels off and `/fav` when it
delights, and those marks set priorities. It runs from `src/companion`. It is a single-user,
local-only project: the git repo has no remote and the bot runs on the owner's machine.

## Where things live

| Where | What |
|---|---|
| `TODO.md` | the work board: Todo, Doing, Done, Canceled, Backlog. Pull work from here |
| `docs/ROADMAP.md` | principles, current state, measured facts, the reasoning behind the order |
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
uv run companion flags | favorites | spend | beliefs | initiative | prompts
uv run companion replay <turn_id> [--show-prompt]   # rebuild a turn; --show-prompt prints everything it sent
uv run companion eval --variants v26.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

Strict ruff and basedpyright, a lefthook pre-commit, and import-linter run on every commit. Layer
rules: `core` imports nothing from the shell, and only `store` imports `sqlite3`. `core` may import
`companion.prompts`, which only reads packaged text.

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
- The memory card, the clock and the notes go in the system block, never in the user's message.
  Anything in the user's message can be read as something the user said, and it leaks into replies.
- Every prompt is a versioned file under `src/companion/prompts/`. Never edit a shipped version: add the
  next `vN.md`, an entry in `prompts/CHANGELOG.md` and a line in `manifest.toml` (`tests/test_prompts.py`
  fails otherwise). A judge's or extractor's logged decision carries `name@version`.
- Dropped and candidate persona versions stay as files. Each `vN.md` has a changelog entry and each
  entry has its file (`tests/test_persona_versions.py` fails otherwise). Never delete a version.
- A prompt change, or a code change that alters what the model is sent, goes in
  `src/companion/prompts/CHANGELOG.md`. Shipping a persona is changing `system/persona` in
  `manifest.toml`. A measurement goes in `evals/CHANGELOG.md`.
- Persona text and public fixtures are general. Nothing in them is about one person. Real turns
  live in `evals/local/`. Inbox notes and docs stay generic and self-contained.
- Read the wall clock only through `core/clock.py` (`utc_now`, `local_zone`). A test enforces it.

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

**Running the bot**
- Settings are environment variables in `.env`: `COMPANION_MODEL`, `COMPANION_SCENE_MODEL`,
  `COMPANION_REFLECT_MODEL`, `COMPANION_DAILY_CAP_USD` (default 10, `off` removes it), `COMPANION_DB`,
  `COMPANION_PACE`, `COMPANION_SPLIT`, `COMPANION_LISTEN`, `COMPANION_INITIATIVE` and
  `COMPANION_PROMPT_OVERRIDES` (try another prompt version without shipping it). The table is in `README.md`.
- The console shows INFO; `data/logs/companion.log` (rotating, not committed) keeps DEBUG with timings
  per stage and the full text of what was said. Secrets are scrubbed by value (`logsetup.py`), and
  `httpx` stays at WARNING because its URLs carry the bot token.
- Never log or print the Telegram token. Telegram errors carry no URL (`TelegramError`).
- Restart with `just restart`, which stops the old process first. Two bots on one token fight over updates. After a
  restart, confirm the "up as" line shows the new prefix and persona.
- A reply the user never received is marked undelivered and left out of what the model reads.
- Replies are held to feel typed: `COMPANION_PACE` is off, quick, natural (default) or slow.
  Set `off` when timing a run by hand. Commands are never held.
- A long, plain reply is sometimes sent as two or three messages (`COMPANION_SPLIT`, on unless `off`).
  The ledger and the history keep it as one reply, so the model never sees the splitting. Cuts fall at
  sentence boundaries only (`core/split.py`).
- A plain message that arrives while the previous one is still being answered (written or held)
  replaces that answer, and the dropped reply is marked undelivered, so the new reply sees both
  messages. Commands never supersede. The poll offset moves past a message when it is queued, so a
  restart can lose one that was queued but not answered.
- Things they said about their near future are recorded as open loops (`core/openloops.py`), and a
  pure gate (`core/initiative.py`) decides every 15 minutes whether to reach out. It only runs in
  shadow mode: it drafts and records `would send` and sends nothing (`COMPANION_INITIATIVE`, `off` to
  disable). Read it with `uv run companion initiative`.
- Each message outside a scene is read for how serious it is before the reply, and code adds a
  listening note (`core/listening.py`). `COMPANION_LISTEN=off` turns it off. Acute messages (severity 3)
  get no note and there is no crisis path yet.
- A message is answered at most once: Telegram updates are recorded before the turn runs.

**Working with the owner**
- Plain English, short, and say what changed and what it was measured on. Lead with what matters.
- "Wait" and "hold" mean do nothing yet. A question is not a request to build.
- Ask before spending beyond a cap, changing the live persona or model in a way that is not a
  reversible measurement, or deleting anything. Decisions the owner has parked stay parked.
- Never run filesystem-wide searches (`find /`, `grep -r` from `$HOME`). Scope to this repo.
- Subagents get the same rules in their brief, including the no-global-search rule, and they are
  read-only unless the task says otherwise.
