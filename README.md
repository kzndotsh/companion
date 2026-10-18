<div align="center">

<h1>Companion</h1>

An AI companion that tries to be as human-like as we can make it, and the memory engine underneath it.

<p>
    <a href="https://www.python.org/downloads/">
        <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white"></a>
    <a href="https://docs.astral.sh/uv/">
        <img alt="uv" src="https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white"></a>
</p>

</div>

> [!WARNING]
> Early and experimental. It is built for one person, it changes all the time, and nothing here is
> guaranteed to work or to stay the same. Use it at your own risk.

It talks like a friend who knows you: it remembers what you told it and who said it, notices when
something is serious, keeps pace like someone typing, and can tell the difference between a story,
a game and the real you. Everything it does is logged with a reason, so any reply can be replayed
and explained.

Today it is reached through Telegram, which is its only integration for now. It is a single-user,
local-only project: it runs on the owner's machine and the repo has no remote.

## What it does

- **Remembers with receipts.** Nothing enters memory without a quote, a speaker and a frame. Beliefs
  go stale and are retired or marked, never deleted ([ADR 0001](docs/adr/0001-a-belief-is-a-quoted-claim-with-a-frame.md),
  [0002](docs/adr/0002-the-ledger-never-deletes.md)).
- **Logs every decision with a reason written by code**, so any turn can be replayed and explained
  ([ADR 0003](docs/adr/0003-every-choice-is-a-decision-with-a-reason.md),
  [0006](docs/adr/0006-decisions-are-logged-by-code.md)).
- **Feels typed.** Replies are paced like a person typing, and long plain replies are sometimes sent
  as two or three messages.
- **Listens.** Each message is read for how serious it is before the reply, and code adds a matching
  note to what the model sees.
- **Remembers what is coming up.** Things the user says about their near future become open loops.
  A gate decides every 15 minutes whether to reach out. It runs in shadow mode only: it drafts and
  records, and sends nothing.
- **Learns from one person's marks.** When a reply feels off they send `/flag`; when one delights
  them they send `/fav`. Those marks, and measurements on recorded turns, decide what gets built next.
- **Measures itself.** A small eval runner replays recorded and scripted turns against persona and
  model variants, with a spend cap on every run.

## Quick start

You need Python 3.12+, [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

```bash
just sync
```

Create a `.env` in the repo root:

```bash
TELEGRAM_BOT_TOKEN=...      # from BotFather
TELEGRAM_USER_ID=...        # the one Telegram user the bot answers
OPENROUTER_API_KEY=...      # models are called through OpenRouter
```

Then start it:

```bash
just run
```

Use `just restart` after a change. It stops the old process first, because two bots on one token
fight over updates. The "up as" line in the log shows which prefix and persona came up.

### Settings

All optional. Set them in `.env`.

| Variable | Effect |
|---|---|
| `COMPANION_MODEL` | model for everyday chat |
| `COMPANION_SCENE_MODEL` | model for pretend scenes |
| `COMPANION_REFLECT_MODEL` | model for memory extraction |
| `COMPANION_DAILY_CAP_USD` | daily spend cap in dollars; `off` removes it |
| `COMPANION_DB` | path to the SQLite database |
| `COMPANION_PACE` | `off`, `quick`, `natural` (default) or `slow`. Use `off` when timing a run by hand |
| `COMPANION_SPLIT` | `off` stops long replies being sent as several messages |
| `COMPANION_LISTEN` | `off` turns off the listening note |
| `COMPANION_INITIATIVE` | `off` disables the shadow-mode reach-out gate |

## Commands

```bash
just check        # lint, types, import layers, tests. Run before every commit
just logs         # follow data/logs/companion.log
just commit "feat(x): msg" path...   # commit only the named files
```

Inspect what the bot has done:

```bash
uv run companion flags          # replies marked /flag
uv run companion favorites      # replies marked /fav
uv run companion beliefs        # what it holds about the user
uv run companion initiative     # what the reach-out gate would have sent
uv run companion spend          # model spend
uv run companion prompts        # every prompt and its current version
uv run companion replay <turn_id>
```

Run an eval:

```bash
uv run companion eval --list
uv run companion eval --variants v22.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

See [evals/README.md](evals/README.md) for how fixtures, variants and judges work.

## How it is built

```
src/companion/
  core/       pure logic: memory, frames, listening, pacing, initiative, the talker
  prompts/    every prompt as versioned text, a manifest and a changelog
  models/     OpenRouter and Anthropic clients
  loops/      the fast and slow loops that call the core
  io/         Telegram
  store/      SQLite, the only place that imports sqlite3
  cli/        the `companion` command
  evals/      the eval runner
```

`core` imports nothing from the shell. import-linter enforces the layers, alongside strict ruff and
basedpyright, a lefthook pre-commit and CI.

### How a reply is made

There is no single big prompt. One talker model writes the reply, and a set of small judges decide
what it gets to see.

1. **Read the message.** Small models label it before the reply starts: how serious it is, whether
   it is real talk, a story, a game or a what-if, and whether it only needs a reaction instead of
   a reply.
2. **Build the card.** Code turns those labels into short notes and adds the clock and the
   relevant memory. The persona is the first system block, the card is the second, and nothing from
   the card ever goes in the user's message.
3. **Write the reply.** The talker sees the persona, the card, the last 40 messages and the new
   message exactly as typed. Pretend scenes are answered by a different model than everyday chat.
4. **Deliver it.** The reply is paced, sometimes split, and sent.
5. **Learn afterwards.** In the background, extractors record what the user said, with quotes, and
   what the companion itself holds as a view. A habit check notices phrases and moves it keeps
   repeating and tells the next turn to vary.

The judges never see the persona, and each logs `name@version` with its decision. Run
`uv run companion replay <turn_id> --show-prompt` to see exactly what a past turn sent. The full
list of prompts and how they fit together is in [src/companion/prompts/](src/companion/prompts/README.md).

### Principles

- **Rough first, then grow from real flags and measurements.** No feature without evidence it is needed.
- **Structural fixes beat prompt rules.** Encode a lesson as a test, a type or a check, not more text.
- **Never rewrite what the model said.** Change what it sees, not what the user sees.
- **Memory, clock and notes go in the system block**, never in the user's message, so the model
  cannot mistake them for something the user said.
- **Every prompt is versioned.** A shipped version is never edited. Add the next `vN.md`, a
  changelog entry and a manifest line.
- **Measure before switching** a model or persona, and say what is measured and what is a guess.

## Where to read more

| Where | What |
|---|---|
| [AGENTS.md](AGENTS.md) | the working rules for anyone, human or agent, changing this repo |
| [KANBAN.md](KANBAN.md) | the work board |
| [docs/ROADMAP.md](docs/ROADMAP.md) | current state, measured facts, and why the work is in this order |
| [docs/adr/](docs/adr) | decisions and their reasons |
| [docs/inbox/](docs/inbox) | ideas that are not yet tasks |
| [docs/research/](docs/research) | audits and studies |
| [src/companion/prompts/](src/companion/prompts/README.md) | every prompt, and how a request is assembled |
| [prompts/CHANGELOG.md](src/companion/prompts/CHANGELOG.md) | every prompt version, with the flag or measurement behind it |
| [evals/CHANGELOG.md](evals/CHANGELOG.md) | what the evals have measured |
