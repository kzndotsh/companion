# Companion (branding TBD)

An AI companion that tries to be as human-like as we can make it, and the memory engine underneath it.

> [!WARNING]
> Early and experimental. It is built for one person, it changes all the time, and nothing here is guaranteed to work or to stay the same. Use it at your own risk.

> [!NOTE]
> Why am I working on this you may ask? As an experiment, and an attempt to better my skills in constructing evaluations while perfecting one of the hardest problems in AI <> Human experiences: memory.

It talks like a friend who knows you. It remembers what you told it and who said it, notices when something is serious, keeps pace like someone typing, and can tell a story, a game and the real you apart. Everything it does is logged with a reason, so any reply can be replayed and explained.

Today it is reached through Telegram, its only integration for now.

## What it does

<details>
<summary><b>Memory</b>: remembers with quotes, shows today's things first, looks things up, tidies itself carefully</summary>

- **Remembers with receipts.** Nothing enters memory without a quote, a speaker and a frame, and
  nothing is ever deleted: memories are retired, closed or marked
  ([ADR 0001](docs/adr/0001-a-belief-is-a-quoted-claim-with-a-frame.md),
  [0002](docs/adr/0002-the-ledger-never-deletes.md), [0010](docs/adr/0010-the-frame-is-set-when-a-message-is-stored.md)).
- **Shows the right memories.** Each turn's card holds fifteen memories. After their boundaries and its
  promises, what they said in the last twelve hours comes first (up to eight), so a meal named this
  afternoon is not crowded off. Sensitive ones only come into view when they are sharing something.
  A one-day moment of daily life, or a personal event on a given
  day, leaves the card a week after it was last mentioned. Feelings and sensitive memories carry a short
  note on what was being talked about ([ADR 0008](docs/adr/0008-beliefs-go-stale-they-are-not-deleted.md), [0012](docs/adr/0012-what-the-model-reads-besides-the-chat-goes-in-the-system-block.md)).
- **Looks things up.** When they ask it to remember, or say it forgot, a small model searches all of
  memory and the finds ride that turn, in a pretend scene too. On every ordinary message, when a memory
  is close to what they said, a small model picks up to two that bear on it and they ride the turn
  ([ADR 0018](docs/adr/0018-memories-that-bear-on-the-moment-chosen-by-embedding-and-a-small-model.md)).
- **Remembers what you did together.** The chat is cut into stretches, each kept as one line on its
  shape and how it ended. When they point at a time ("last night") or come back after a gap, the lines
  for that time ride the turn (J12).
- **Tidies itself, carefully.** A nightly check closes passing moments, a new memory that repeats an
  old one becomes evidence on it, and memories about one thing are proposed as one for the owner to
  accept, but only where a judge matched the owner's own review. Each new memory is labelled about
  their life, about the bot (dropped) or one day's routine (kept a week). Everything else
  is a question for the owner ([ADR 0019](docs/adr/0019-memory-tidies-itself-only-where-a-judge-matched-the-owner.md)).
- **Gets to know them.** It asks what to call them, then their pronouns, keeps how they want to be
  referred to pinned in every turn, labels each memory by part of their life, and works out (in shadow) what it knows least
  and when their own words open the door to asking a basic it does not know.
- **Asks about conflicts.** A new memory that may replace or contradict an older one is a question for
  the owner, who keeps one or both ([ADR 0019](docs/adr/0019-memory-tidies-itself-only-where-a-judge-matched-the-owner.md)).

</details>

<details>
<summary><b>Listening and care</b>: reads how serious a message is, tells a real risk from a joke, repairs, checks in</summary>

- **Listens.** Each message is read for how serious it is before the reply, and code adds a matching note ([ADR 0014](docs/adr/0014-models-label-and-code-chooses-the-note.md)).
- **Takes a real risk seriously, and a joke as a joke.** A message that may be a risk to their life is
  read three times by a risk judge; code picks the level and fails safe. At concern it asks them
  directly and warmly and names a crisis line once; at urgent code also sends a fixed message with the
  line after the reply. Shadow by default ([ADR 0022](docs/adr/0022-a-crisis-path-for-acute-messages.md)).
- **Repairs.** When they say it got them wrong, it owns it in a line instead of improvising, and it
  never asks them to repeat something memory already holds. Once it has owned a slip, a note after the
  history tells it that was enough, so it does not pile on apologies.
- **Checks in.** Coming back hours after a talk that turned serious, it gently asks how they are now,
  once.

</details>

<details>
<summary><b>Plans, reminders and days</b>: follows up on plans, keeps reminders, knows the date and notices the day, paces like typing</summary>

- **Follows up.** Things they say about their near future become open loops. When one falls due, it is
  brought up lightly the next time they write. Reaching out first, about a plan, after they stepped
  away or for its own reasons (a thought, a time they keep, missing them, at a share of conversations
  the owner sets), runs in shadow only; with the crisis path on it is held for a day after a risk turn
  ([ADR 0021](docs/adr/0021-reaching-out-for-its-own-reasons-inside-a-code-gate.md), [0015](docs/adr/0015-initiative-reaches-out-only-about-their-own-firm-plans-through-a-code-gate.md)).
- **Reminds them.** "Remind me at 8pm to take the dog out" or "check up on me in a few days about the
  interview": a small model reads the words, code works out the time and asks when it is unclear, and
  the reminder comes when due in its own voice. One-off only; a pretend scene holds it until it ends.
- **Knows the date.** The clock line gives the weekday, the date and the time, so it can place what
  they name.
- **Notices the day.** On a casual turn code may add one note after the history: a warm or fun US
  public or cultural day ("if it fits", never assuming they celebrate it), the lead-up to a big one,
  or a month, a hundred days, six months or a year since they first talked. Each is offered once, and
  no model chooses it (`features/calendar`, [ADR 0014](docs/adr/0014-models-label-and-code-chooses-the-note.md)).
- **Keeps track of what is coming.** When they say dinner is on its way or they will shower soon, a
  small model labels the message and code keeps it open until they say it happened, they are back, or
  it is well past its time; meanwhile one line after the history says it has not happened yet, so the
  reply does not ask how the food was. Shadow by default (`features/now`,
  [ADR 0024](docs/adr/0024-what-they-said-is-coming-is-tracked-until-it-happens.md)).
- **Feels typed.** Replies are paced like a person typing, and long plain replies are sometimes sent
  as two or three messages. A new message that arrives first replaces the reply in progress; a reply
  cut off part way is remembered as only the part they received.

</details>

<details>
<summary><b>Its own character</b>: its own tastes, moods and emoticons, plays along, does not interview</summary>

- **Moves on.** When a small topic has run its course, it reacts and moves the chat on instead of
  asking about smaller and smaller details.
- **Has tastes of its own.** It picks for itself and keeps its view under pushback without a reason
  (persona v41). The views it states about itself are sorted, and the tastes among them are shown back
  to it when a message touches them, so what it likes stays the same from day to day
  ([ADR 0020](docs/adr/0020-the-companions-own-lore-lives-in-its-views-labelled-by-kind-and-shown-when-the-moment-touches-it.md), [0009](docs/adr/0009-the-companions-views-are-recorded-and-gated-not-hand-approved.md), [0011](docs/adr/0011-the-companion-is-a-knowledgeable-friend-with-its-own-growing-personality.md)).
- **Plays along with a guess.** When a short question invites one ("you know what time it is?"), it
  makes one playful guess from what memory holds, as a question; a hint at what it is time for is
  looked up as one of their habits or routines.
- **Does not interview.** After three replies in a row that each asked a question, a note after the
  history says to ask none this time but still leave them something to answer.
- **Keeps a question game going.** When they ask it to keep asking them things ("ask me anything"), a
  note after the history asks it for the next question, outside scenes and serious turns.
- **Has emoticons of its own.** On casual turns code offers it one of its own marks and kaomoji; when
  their message has one, the note names that one as theirs, so it stops copying it.
- **Reacts like a person to small vents.** A short reaction, with varied size examples drawn per turn so
  it does not say the same line every time.
- **Has a mood that carries.** Cozy, tender or playful, kept by code from what happened, shown only in
  how it replies ([ADR 0016](docs/adr/0016-a-mood-that-carries-owned-by-code-shown-in-behaviour.md)).

</details>

<details>
<summary><b>Safety and models</b>: two talkers above a fixed floor, checks its own replies, never goes silent</summary>

- **Routes roleplay to a second model.** Pretend scenes, and intimate talk if the operator allows it
  (once one of their messages is explicit; flirting stays with the everyday model), go to a less
  restrictive model, above an age floor in code that no setting changes
  ([ADR 0017](docs/adr/0017-the-operator-decides-where-intimate-talk-goes-above-a-fixed-floor.md)).
  A lone short reaction in asterisks ("\*explodes\*") does not start a scene on its own, and the
  scene reminder keeps it at their level: as far as they take it, explicit only when they are.
- **Checks its own replies.** A reply with a known habit (an em dash, an AI disclaimer nobody asked for,
  the clock line copied from its own notes, the stock "X, especially when" or "X, even when" line, the stage
  direction "a beat", markdown that shows raw in a chat, and on ordinary turns a joke bolted onto an
  ordinary message or a canned reaction that could sit under any message) is drawn once more, twice
  if an em dash survives, and so is an empty reply.
  Nothing is ever edited.
- **Never goes silent.** If the talker errors, or has not answered in ten seconds, a fallback model
  answers too and the first reply wins.
- **Judges per model.** The judges share one small model, with a second for calls it refuses; a judge
  can be given its own model (`COMPANION_JUDGE_MODELS`), and the crisis risk judge reads on DeepSeek
  first, since the shared model's provider refused many crisis messages.
- **Stops without losing a message.** On a stop or restart it fetches nothing more and answers what it
  already received, the reply in progress included, for up to 30 seconds.

</details>

<details>
<summary><b>Running and learning</b>: every decision logged, backups, flags and favourites, evals</summary>

- **Logs every decision with a reason written by code**
  ([ADR 0003](docs/adr/0003-every-choice-is-a-decision-with-a-reason.md),
  [0006](docs/adr/0006-decisions-are-logged-by-code.md), [0013](docs/adr/0013-every-prompt-is-a-versioned-file.md)).
- **Backs itself up** at every start and once a day, each copy checked.
- **Learns from one person's marks.** `/flag` a reply that feels off, `/fav` one that delights. Those
  marks, and measurements on recorded turns, decide what gets built next. `/mode` answers which model
  wrote the last reply and whether a scene is under way. None of the three ever reaches the model.
- **Measures itself.** An eval runner replays recorded and scripted turns against persona and model
  variants, with a spend cap, the real OpenRouter charge, and a margin of error on every result. A
  sample is made by the turn's own code: its notes, its request and its reply checks and redraws
  (`+raw` skips them), so it is what they would have received. The
  made-up facts rate (`companion invented`) counts replies that state something about them that
  nothing supports ([ADR 0007](docs/adr/0007-evals-replay-recorded-turns-with-a-small-own-runner.md)).

</details>

## What runs in shadow

We often try new behaviour in shadow first: it works out and logs what it would do, but changes
nothing in the chat until a review shows it reads right. Right now that includes reaching out first,
the crisis path, the nightly memory check, the mood and the getting-to-know-you questions. The full
list, with each one's setting and review date, is in [AGENTS.md](AGENTS.md#what-runs-in-shadow).

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

To talk on Discord instead, add the three lines below (setup: [docs/delivery.md](docs/delivery.md#discord-setup)).
`TELEGRAM_USER_ID` stays: it names the relationship and its database, so it is the same companion
and the same memory on either surface.

```bash
COMPANION_SURFACE=discord
DISCORD_BOT_TOKEN=...       # from the Discord Developer Portal
DISCORD_USER_ID=...         # the one Discord user the bot answers
```

Then start it:

```bash
just run
```

Use `just restart` after a change. It stops the old process first, because two bots on one token
fight over updates. The "up as" line shows the persona, the prompt set, the models and every
setting with its value.

### Settings

All optional. Set them in `.env`.

<details>
<summary><b>Models</b> (7): which model talks, judges and embeds</summary>

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_MODEL` | `openai/gpt-6-luna` | the everyday talker |
| `COMPANION_ROLEPLAY_MODEL` | `deepseek/deepseek-v4.1-flash` | pretend scenes, and intimate talk when allowed; `none` uses the everyday model |
| `COMPANION_TALKER_FALLBACK` | the roleplay model | answers when the everyday talker errors or has not replied in 10 s (first answer wins); the roleplay talker falls back to the everyday model; `none` turns it off |
| `COMPANION_REFLECT_MODEL` | `anthropic/claude-haiku-5.5` | the judges and the memory pass, except a judge named in `COMPANION_JUDGE_MODELS` |
| `COMPANION_FALLBACK_MODEL` | `deepseek/deepseek-v4.1-flash` | asked only when the judges' model refuses a call; the floor never relies on its answers; `none` disables it |
| `COMPANION_JUDGE_MODELS` | `crisis=deepseek/deepseek-v4.1-flash` | a model per judge, as `judge=provider/model` pairs separated by commas: a judge named here reads on that model first and on the judges' model when it refuses (that answer counts as the fallback's). The default puts the crisis risk judge on DeepSeek, since Haiku's provider refuses many crisis messages; `none` sends every judge to the judges' model. A malformed value stops the bot at start |
| `COMPANION_EMBED_MODEL` | `openai/text-embedding-3-small` | embeddings for the memory look-up and the repeat check |

</details>

<details>
<summary><b>Behaviour</b> (15): what it does on each turn</summary>

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_CHARACTER` | none | `mika` lays the sheet `data/characters/mika.md` (private, never committed) over the persona; a public sheet could live in `prompts/characters/mika/`, though none ships yet. A `## In roleplay and intimate moments` section reaches only the roleplay model, and a `## Scene reminder` section is sent after the history on roleplay turns. A `## Crisis message` section is the fixed message code sends with the crisis line on an urgent turn (`$line` filled in by code; ADR 0022), and no model sees it. It still says it is an AI when sincerely asked |
| `COMPANION_ROUTE_INTIMATE` | off | `on` lets intimate talk go to the roleplay model (ADR 0017), above an age floor in code that no setting changes |
| `COMPANION_LISTEN` | on | the listening note before each reply; `off` turns it off |
| `COMPANION_MOOD` | `shadow` | `on` adds the mood line, `shadow` works it out and logs it, `off` does neither |
| `COMPANION_RESAMPLE` | on | a reply that fails a check is drawn once more; `off` disables it |
| `COMPANION_SURFACE` | `telegram` | which chat it runs on: `telegram` (needs `TELEGRAM_BOT_TOKEN`) or `discord` (needs `DISCORD_BOT_TOKEN` and `DISCORD_USER_ID`); one at a time, one relationship and one memory either way |
| `COMPANION_PACE` | `natural` | how long replies are held to feel typed: `off`, `quick`, `natural` or `slow` |
| `COMPANION_SPLIT` | on | long plain replies are sometimes sent as two or three messages; `off` stops it |
| `COMPANION_RELEVANCE` | `on` | memories that bear on their message, picked when one is near and shown to it (ADR 0018); `shadow` only logs, `off` stops it |
| `COMPANION_EPISODES` | `on` | what the two of them did recently, shown when they point at a time or come back after a gap (J12); `shadow` only logs, `off` stops it |
| `COMPANION_MARKS` | `on` | one of its own emoticons offered after the history on casual turns: always when their message has one, else about one in four; never theirs or a recent one (`features/marks`); `off` stops it |
| `COMPANION_LOOP_NOTES` | `loose` | a hedged plan of theirs ("may watch a movie tonight") becomes a note-only loop, asked once when they next write and never a reach-out (`features/threads`); `off` keeps only firm plans |
| `COMPANION_REMINDERS` | on | reminders and check-ins they ask for, one-off, sent when due (J50); `off` stops reading and sending them |
| `COMPANION_CALENDAR` | `on` | one note after the history on a casual turn about the day: a US public or cultural day, the lead-up to a big one, or the relationship's month, hundred days or years (`features/calendar`); `off` stops it |
| `COMPANION_NOW` | `shadow` | what they said is coming, kept until it happens (ADR 0024): `on` sends one line after the history while it is open ("about 2 minutes ago they said dinner is coming soon; it has not happened unless they say so"), `shadow` logs the line and sends nothing, `off` stops the note; the reader also runs while reaching out is on, for nudges |
| `COMPANION_LORE` | `on` | show it its own tastes nearest their message on ordinary turns (ADR 0020); `shadow` only logs, `off` skips it |

</details>

<details>
<summary><b>Shadow features</b> (5): what logs before it goes live</summary>

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_INITIATIVE` | `shadow` | the reach-out gate drafts and records but sends nothing; `off` disables it |
| `COMPANION_REACH` | `warm` | the dial for reaching out for its own reasons (ADR 0021): the share of conversations over the last 14 days it may start, `rare` 1/8, `light` 1/5, `normal` 1/4, `warm` 1/3, `clingy` 1/2, at least 6 hours apart; `off` stops these kinds only. In shadow a would-send counts as a conversation it started, so shadow holds the way live would |
| `COMPANION_CONSOLIDATE` | `shadow` | the memory check (ADR 0019): `on` acts, `shadow` only logs, `off` skips it |
| `COMPANION_PROMISES` | `shadow` | read its own replies for promises it made (J12) and record them; `off` skips it |
| `COMPANION_CRISIS` | `shadow` | the crisis path (ADR 0022): `shadow` reads a message that is serious or uses crisis words for risk and logs the level and what it would do, `on` acts (the concern note, the fixed crisis-line message at urgent, a scene set aside for the turn, a reply that names means drawn once more, a day's hold on reaching out first), `off` skips it |

</details>

<details>
<summary><b>Running</b> (4): spend cap, backups, database, prompt overrides</summary>

| Variable | Default | What it does |
|---|---|---|
| `COMPANION_DAILY_CAP_USD` | `10` | daily spend cap in dollars; `off` removes it |
| `COMPANION_BACKUP_DIR` | `data/backups` | where snapshots go; point it at another drive or a synced folder, since a copy on the same disk does not survive the disk |
| `COMPANION_DB` | the one database in `data/` | the SQLite database, for the CLI commands |
| `COMPANION_PROMPT_OVERRIDES` | none | `system/ack=v1,notes/length=v2` runs other prompt versions without shipping them; set before the process starts |

</details>

## Commands

```bash
just check        # lint, types, import layers, tests; run before every commit
just run          # start the bot
just restart      # stop the running bot, then start it here
just logs         # follow data/logs/companion.log
just commit "feat(x): msg" path...   # commit only the named files
```

In the Telegram chat:

```text
/flag [kind] note mark the last reply; kind is off (default), forgot, too_much or unwanted
/fav [note]       mark the last reply as one you loved
                  send /flag or /fav as a reply to one of its messages to mark that reply instead
/mode             which model wrote the last reply and why, and whether a scene is under way
```

<details>
<summary><b>See what the bot has done</b>: flags, favourites, replays, spend, shadows, crisis, prompts</summary>

```bash
uv run companion flags          # replies marked /flag; --to-fav ID moves one to favourites
uv run companion favorites      # replies marked /fav
uv run companion replay <turn_id> --show-prompt   # rebuild a turn and everything it sent
uv run companion spend          # model spend by purpose
uv run companion initiative     # open loops, and what reaching out would have sent
uv run companion mood           # the mood now; --replay DAYS rebuilds it over past messages
uv run companion map            # what it knows by part of their life; --label labels new memories
uv run companion episodes       # the times they spent together, one line each; --write writes new ones
uv run companion callbacks      # judge recent replies for callbacks to memories
uv run companion invented --days 7 --cap 0.2 --dump out.json   # made-up facts about them: candidates, to confirm by a stronger reader
uv run companion prompts        # every prompt and its current version
uv run companion shadows        # every feature in shadow, its review date, overdue first
uv run companion crisis         # crisis levels read lately and lines sent (counts only)
uv run companion crisis --check --cap 0.10   # the risk judge on the public crisis fixtures (paid)
```

</details>

<details>
<summary><b>Look after memory</b>: beliefs, reviews, merges, views, lore, names, promises, reminders, calendar, backups</summary>

```bash
uv run companion beliefs        # what it holds about the user, with quotes
uv run companion memory review  # answer the memory check's questions and merge proposals until you quit
uv run companion memory group   # group memories about one thing across the whole store into merge proposals
uv run companion memory context # write the missing notes on what a feeling or sensitive memory was about
uv run companion memory label   # keep-label memories kept before the rule; each change becomes a question
uv run companion opinions       # its own views, tentative or settled
uv run companion views          # how its views reach the card; --mode auto, review or off
uv run companion approve <id>   # let one of its own views reach the card
uv run companion lore           # its own tastes (lore); --label labels new views, --relabel all of them
uv run companion names          # things named in memory; --read reads new memories for names first
uv run companion promises       # the promises it made; --not ID if one is not a promise, --retire ID
uv run companion reminders      # the reminders they asked for and what became of each; --cancel ID
uv run companion calendar       # the occasions in the next 30 days, lead-ups included, and what was offered lately
uv run companion retire <id> --reason "..."      # close one memory
uv run companion merge <id> <id> --claim "..."   # merge memories that say one thing, keeping every quote
uv run companion address        # how they want to be referred to; --set TEXT changes it
uv run companion backup         # snapshot now; --list, or --restore FILE with the bot stopped
uv run companion reflect        # run the memory pass now instead of waiting for a quiet moment; --from-start rereads it all
uv run companion dedupe         # close memories that rest on the same words
uv run companion rebuild        # restate every memory under the current rules
uv run companion calibrate      # compare the automatic gates with your approvals
```

</details>

<details>
<summary><b>Run an eval</b>: list, dry run, a capped run</summary>

```bash
uv run companion eval --list
uv run companion eval --variants v41.md,v41.md+raw --samples 12 --cap 0.2 --dry-run
uv run companion eval --variants v41.md@openai/gpt-6-luna --samples 12 --cap 0.2
```

</details>

A run shows the OpenRouter balance first and refuses a cap above it. Each result carries its 95%
range, and two variants are compared for whether the gap is real or within noise. See
[evals/README.md](evals/README.md) for fixtures, variants and judges.

## How it is built

```
companion/
├── src/companion/        the bot
│   ├── turn/             what happens to one message, from reading it to replying
│   ├── memory/           building and tidying memory, between messages and overnight
│   ├── features/         one folder per feature, each with a README on how it works
│   ├── prompts/          every text the models are given, each version kept
│   ├── core/  loops/     shared rules and building blocks the features use
│   ├── models/           talking to the AI models
│   ├── io/               talking to Telegram, pacing replies like typing
│   ├── store/            the database
│   ├── cli/              the `companion` command
│   ├── evals/            the eval runner
│   ├── lib/              small general helpers
│   ├── daemon.py         starts the bot
│   ├── settings.py       reads the settings
│   └── registry.py       the list of features
├── tests/                automatic tests, run before every commit
├── evals/                test conversations, and what was measured
├── docs/                 how things work, decisions (adr/) and ideas (inbox/)
├── scripts/              small helpers, like the one behind `just restart`
└── data/                 your private data: database, logs, backups. Never committed
```

The code is kept in layers that only use the layers below them, checked on every commit. The details,
for anyone changing it, are in [AGENTS.md](AGENTS.md).

### How a reply is made, and what runs in the background

There is no single big prompt: one talker model writes the reply, and small judges and code decide
what it sees. Each message passes through a few stages (read, route, look things up, assemble, talk
and check, store), described in [docs/turn.md](docs/turn.md), with Telegram delivery in
[docs/delivery.md](docs/delivery.md). Beside the chat, timers run the memory pass after a quiet spell
and the night's memory work at 04:00 ([docs/memory.md](docs/memory.md)), the reach-out tick every 15
minutes and reminders every minute ([docs/initiative.md](docs/initiative.md)), and a backup at every
start and once a day. Every prompt, and how a request is put together, is in
[src/companion/prompts/](src/companion/prompts/README.md).

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
| [docs/turn.md](docs/turn.md), [delivery.md](docs/delivery.md), [initiative.md](docs/initiative.md), [memory.md](docs/memory.md) | how a reply is made, how Telegram delivery works, plans and reach-outs, and memory over time |
| `src/companion/features/<name>/README.md` | how each feature works, with its files, prompts, setting and what was measured |
| [TODO.md](TODO.md) | the work board and the plan: where we are, measured facts, what comes next |
| [docs/adr/](docs/adr) | decisions and their reasons |
| [docs/inbox/](docs/inbox) | ideas that are not yet tasks |
| `docs/research/` | audits and studies (local only, not committed) |
| [src/companion/prompts/](src/companion/prompts/README.md) | every prompt, and how a request is assembled |
| [prompts/CHANGELOG.md](src/companion/prompts/CHANGELOG.md) | every prompt version, with the flag or measurement behind it |
| [evals/README.md](evals/README.md), [evals/CHANGELOG.md](evals/CHANGELOG.md) | how evals work, and what they have measured |

## License

GNU Affero General Public License, version 3 or later. See [LICENSE](LICENSE).
