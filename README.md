# Companion (branding TBD)

An AI companion that tries to be as human-like as we can make it, and the memory engine underneath it.

> [!WARNING]
> Early and experimental. It is built for one person, it changes all the time, and nothing here is guaranteed to work or to stay the same. Use it at your own risk.

> [!NOTE]
> Why am I working on this you may ask? As an experiment, and an attempt to better my skills in constructing evaluations while perfecting one of the hardest problems in AI <> Human experiences: memory.

It talks like a friend who knows you. It remembers what you told it and who said it, notices when something is serious, keeps pace like someone typing, and can tell a story, a game and the real you apart. Everything it does is logged with a reason, so any reply can be replayed and explained.

Today it is reached through Telegram, its only integration for now.

## What it does

**Memory**

- **Remembers with receipts.** Nothing enters memory without a quote, a speaker and a frame, and
  nothing is ever deleted: memories are retired, closed or marked
  ([ADR 0001](docs/adr/0001-a-belief-is-a-quoted-claim-with-a-frame.md),
  [0002](docs/adr/0002-the-ledger-never-deletes.md)).
- **Shows the right memories.** Each turn's card holds fifteen memories. Sensitive ones only come into
  view when they are sharing something, and a one-day moment of daily life leaves the card a week
  after it was last mentioned.
- **Looks things up.** When they ask it to remember, or say it forgot, a small model searches all of
  memory and the finds ride that turn, in a pretend scene too. A look-up of what bears on every
  message runs in shadow ([ADR 0018](docs/adr/0018-memories-that-bear-on-the-moment-chosen-by-embedding-and-a-small-model.md)).
- **Tidies itself, carefully.** A nightly check closes passing moments, and a new memory that repeats an
  old one becomes evidence on it, but only where a judge matched the owner's own review. Everything else
  is a question for the owner ([ADR 0019](docs/adr/0019-memory-tidies-itself-only-where-a-judge-matched-the-owner.md)).
- **Gets to know them.** It asks what to call them, keeps how they want to be referred to pinned in
  every turn, labels each memory by part of their life, and works out (in shadow) what it knows least.

**Conversation**

- **Listens.** Each message is read for how serious it is before the reply, and code adds a matching note.
- **Repairs.** When they say it got them wrong, it owns it in a line instead of improvising, and it
  never asks them to repeat something memory already holds.
- **Follows up.** Things they say about their near future become open loops. When one falls due, it is
  brought up lightly the next time they write. Reaching out first runs in shadow only.
- **Moves on.** When a small topic has run its course, it reacts and moves the chat on instead of
  asking about smaller and smaller details.
- **Has a mood that carries.** Cozy, tender or playful, kept by code from what happened, shown only in
  how it replies ([ADR 0016](docs/adr/0016-a-mood-that-carries-owned-by-code-shown-in-behaviour.md)).
- **Feels typed.** Replies are paced like a person typing, and long plain replies are sometimes sent
  as two or three messages.

**Safety and models**

- **Routes roleplay to a second model.** Pretend scenes, and intimate talk if the operator allows it,
  go to a less restrictive model, above an age floor in code that no setting changes
  ([ADR 0017](docs/adr/0017-the-operator-decides-where-intimate-talk-goes-above-a-fixed-floor.md)).
- **Checks its own replies.** A reply with a known habit (an em dash, a joke bolted onto an ordinary
  message, an AI disclaimer nobody asked for, the clock line copied from its own notes) is drawn once more. Nothing is ever edited.
- **Never goes silent.** If the talker errors, or has not answered in ten seconds, a fallback model
  answers too and the first reply wins.

**Running and learning**

- **Logs every decision with a reason written by code**
  ([ADR 0003](docs/adr/0003-every-choice-is-a-decision-with-a-reason.md),
  [0006](docs/adr/0006-decisions-are-logged-by-code.md)).
- **Backs itself up** at every start and once a day, each copy checked.
- **Learns from one person's marks.** `/flag` a reply that feels off, `/fav` one that delights. Those
  marks, and measurements on recorded turns, decide what gets built next.
- **Measures itself.** An eval runner replays recorded and scripted turns against persona and model
  variants, with a spend cap, the real OpenRouter charge, and a margin of error on every result.

## What runs in shadow

Some features are new enough that they only log what they would do. Each is turned on by a setting
once its log has been read.

| Feature | Setting | Read it with |
|---|---|---|
| Reaching out first about a due plan | `COMPANION_INITIATIVE` | `companion initiative` |
| The look-up of memories that bear on each message | `COMPANION_RELEVANCE` | the decision log |
| What it would ask to get to know them | always shadow for now | `companion map` |
| The nightly memory check and the write-time repeat check | `COMPANION_CONSOLIDATE` | `companion memory review`, the decision log |
| The mood (shadow by default; can be `on`) | `COMPANION_MOOD` | `companion mood` |
| The promises it made in its own replies (J12) | `COMPANION_PROMISES` | `companion promises` |
| Memories about a name they mention, left off the card | always shadow for now | `companion names` |

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
fight over updates. The "up as" line shows the persona, the prompt set, the models and every
setting that is on or in shadow.

### Settings

All optional. Set them in `.env`.

**Models**

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_MODEL` | `openai/gpt-6-luna` | the everyday talker |
| `COMPANION_ROLEPLAY_MODEL` | `deepseek/deepseek-v4.1-flash` | pretend scenes, and intimate talk when allowed; `none` uses the everyday model |
| `COMPANION_TALKER_FALLBACK` | the roleplay model | answers when the everyday talker errors or has not replied in 10 s (first answer wins); the roleplay talker falls back to the everyday model; `none` turns it off |
| `COMPANION_REFLECT_MODEL` | `anthropic/claude-haiku-5.5` | the judges and the memory pass |
| `COMPANION_FALLBACK_MODEL` | `deepseek/deepseek-v4.1-flash` | asked only when the judges' model refuses a call; the floor never relies on its answers; `none` disables it |
| `COMPANION_EMBED_MODEL` | `openai/text-embedding-3-small` | embeddings for the memory look-up and the repeat check |

**Behaviour**

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_CHARACTER` | none | `mika` lays the sheet `data/characters/mika.md` (private) or `prompts/characters/mika/` (public) over the persona. A `## In roleplay and intimate moments` section reaches only the roleplay model. It still says it is an AI when sincerely asked |
| `COMPANION_ROUTE_INTIMATE` | off | `on` lets intimate talk go to the roleplay model (ADR 0017), above an age floor in code that no setting changes |
| `COMPANION_LISTEN` | on | the listening note before each reply; `off` turns it off |
| `COMPANION_MOOD` | `shadow` | `on` adds the mood line, `shadow` works it out and logs it, `off` does neither |
| `COMPANION_RESAMPLE` | on | a reply that fails a check is drawn once more; `off` disables it |
| `COMPANION_PACE` | `natural` | how long replies are held to feel typed: `off`, `quick`, `natural` or `slow` |
| `COMPANION_SPLIT` | on | long plain replies are sometimes sent as two or three messages; `off` stops it |

**Shadow features**

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_INITIATIVE` | `shadow` | the reach-out gate drafts and records but sends nothing; `off` disables it |
| `COMPANION_RELEVANCE` | `shadow` | the look-up of memories that bear on each message (ADR 0018); `off` stops it |
| `COMPANION_CONSOLIDATE` | `shadow` | the memory check (ADR 0019): `on` acts, `shadow` only logs, `off` skips it |
| `COMPANION_PROMISES` | `shadow` | read its own replies for promises it made (J12) and record them; `off` skips it |

**Running**

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_DAILY_CAP_USD` | `10` | daily spend cap in dollars; `off` removes it |
| `COMPANION_BACKUP_DIR` | `data/backups` | where snapshots go; point it at another drive or a synced folder, since a copy on the same disk does not survive the disk |
| `COMPANION_DB` | the one database in `data/` | the SQLite database, for the CLI commands |
| `COMPANION_PROMPT_OVERRIDES` | none | `system/ack=v1,notes/length=v2` runs other prompt versions without shipping them; set before the process starts |

## Commands

```bash
just check        # lint, types, import layers, tests; run before every commit
just run          # start the bot
just restart      # stop the running bot, then start it here
just logs         # follow data/logs/companion.log
just commit "feat(x): msg" path...   # commit only the named files
```

See what the bot has done:

```bash
uv run companion flags          # replies marked /flag
uv run companion favorites      # replies marked /fav
uv run companion replay <turn_id> --show-prompt   # rebuild a turn and everything it sent
uv run companion spend          # model spend by purpose
uv run companion initiative     # open loops, and what reaching out would have sent
uv run companion mood           # the mood now; --replay DAYS rebuilds it over past messages
uv run companion map            # what it knows by part of their life; --label labels new memories
uv run companion callbacks      # judge recent replies for callbacks to memories
uv run companion prompts        # every prompt and its current version
```

Look after memory:

```bash
uv run companion beliefs        # what it holds about the user, with quotes
uv run companion memory review  # answer the memory check's questions, a few at a time
uv run companion names          # things named in memory; --read reads new memories for names first
uv run companion promises       # the promises it made; --not ID if one is not a promise, --retire ID
uv run companion retire <id> --reason "..."      # close one memory
uv run companion merge <id> <id> --claim "..."   # merge memories that say one thing, keeping every quote
uv run companion address        # how they want to be referred to; --set TEXT changes it
uv run companion backup         # snapshot now; --list, or --restore FILE with the bot stopped
uv run companion reflect        # run the memory pass now instead of waiting for a quiet moment
```

Run an eval:

```bash
uv run companion eval --list
uv run companion eval --variants v40.md,v40.md+listen --samples 12 --cap 0.2 --dry-run
uv run companion eval --variants v40.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

A run shows the OpenRouter balance first and refuses a cap above it. Each result carries its 95%
range, and two variants are compared for whether the gap is real or within noise. See
[evals/README.md](evals/README.md) for fixtures, variants and judges.

## How it is built

```
src/companion/
  core/        pure logic: memory, the card, listening, frames, the floor, mood, open loops,
               relevance, consolidation, pacing and splitting
  prompts/     every prompt as versioned text, with a manifest and a changelog
  models/      OpenRouter and Anthropic clients, embeddings, the fallbacks, the credits meter
  loops/       the fast loop (one turn) and the slow loop (memory, open loops, the nightly check)
  io/          Telegram
  store/       SQLite, the only place that imports sqlite3, and the backups
  cli/         the `companion` command
  evals/       the eval runner and its statistics
  daemon.py    starts it all, reads the settings
```

`core` imports nothing from the shell. import-linter enforces the layers, alongside strict ruff and
basedpyright, a lefthook pre-commit and CI.

### How a reply is made

There is no single big prompt. One talker model writes the reply, and a set of small judges decide
what it gets to see.

1. **Read the message.** Small models label it before the reply starts: how serious it is, whether
   it is real talk, a story, a game or a what-if, whether it only needs a reaction, whether they ask
   it to remember or say it got them wrong, and whether a small topic has run its course.
2. **Build the card.** Code turns those labels into short notes and adds the clock, how they want to
   be referred to, the memories in view, anything looked up, a due plan of theirs and the mood. The
   persona is the first system block and the card is the second, with the clock and the notes in
   `<clock>` and `<notes>` tags. Nothing from the card ever goes in the user's message.
3. **Write the reply.** The talker sees the persona, the card, the last 40 messages and the new
   message exactly as typed. Pretend scenes, and intimate talk when allowed, go to the roleplay model,
   unless the floor keeps them on the everyday one. A stall or an error goes to the fallback model.
4. **Check and deliver it.** A reply that fails a check is drawn once more. Then it is paced,
   sometimes split (never roleplay), and sent.

The judges never see the persona, and each logs `name@version` with its decision. The full list of
prompts and how a request is assembled is in [src/companion/prompts/](src/companion/prompts/README.md).

### What happens in the background

- **After 90 seconds of quiet,** the memory pass reads the new messages and records what the user said,
  with quotes, and the companion's own views. A new memory that repeats an old one is checked against
  it. A separate pass, with its own bookmark, records the plans they mention.
- **Every 15 minutes,** the reach-out gate looks at due plans (shadow).
- **At 04:00,** the memory check reads each settled memory (shadow).
- **At every start and once a day,** the database and character sheets are backed up.

### Principles

- **Rough first, then grow from real flags and measurements.** No feature without evidence it is needed.
- **Structural fixes beat prompt rules.** Encode a lesson as a test, a type or a check, not more text.
- **Never rewrite what the model said.** Change what it sees, not what the user sees.
- **Memory, clock and notes go in the system block**, never in the user's message, so the model
  cannot mistake them for something the user said.
- **Every prompt is versioned.** A shipped version is never edited. Add the next `vN.md`, a
  changelog entry and a manifest line.
- **Measure before switching** a model or persona, say what is measured and what is a guess, and
  say when a difference is within noise.

## Your data

Everything private lives in `data/`, which is never committed: the database (every message, memory,
flag and decision), the logs, private character sheets and the backups. Snapshots are taken at every
start and once a day; the newest 7 daily and 7 others are kept, and each is checked before it counts.
Real turns used as test fixtures live in `evals/local/`, also never committed. Secrets are scrubbed
from the logs by value.

## Where to read more

| Where | What |
|---|---|
| [AGENTS.md](AGENTS.md) | the working rules for anyone, human or agent, changing this repo |
| [TODO.md](TODO.md) | the work board and the plan: where we are, measured facts, what comes next |
| [docs/adr/](docs/adr) | decisions and their reasons |
| [docs/inbox/](docs/inbox) | ideas that are not yet tasks |
| `docs/research/` | audits and studies (local only, not committed) |
| [src/companion/prompts/](src/companion/prompts/README.md) | every prompt, and how a request is assembled |
| [prompts/CHANGELOG.md](src/companion/prompts/CHANGELOG.md) | every prompt version, with the flag or measurement behind it |
| [evals/README.md](evals/README.md), [evals/CHANGELOG.md](evals/CHANGELOG.md) | how evals work, and what they have measured |

## License

GNU Affero General Public License, version 3 or later. See [LICENSE](LICENSE).
