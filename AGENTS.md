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
| `TODO.md` | the work board and the plan: where we are, measured facts, Now, Next and Later, the decisions waiting on the owner, then the cards (Doing, Todo, Backlog, Done, Canceled). Pull work from here |
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
uv run companion flags | favorites | spend | beliefs | initiative | prompts | callbacks | mood | address | map | backup
uv run companion memory review | group | promises | names | lore   # questions for the owner, merge proposals, shadow lists
uv run companion reminders [--cancel ID]   # the reminders they asked for and what became of each
uv run companion invented --days 7 --cap 0.2 --dump F.json   # made-up facts candidates; confirm with a Claude judge
uv run companion replay <turn_id> [--show-prompt]   # rebuild a turn; --show-prompt prints everything it sent
uv run companion eval --variants v41.md@openai/gpt-6-luna --samples 12 --cap 0.2
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
- A line for the system block is a note source in `loops/notes.py` `SOURCES`, in the order it is sent:
  it reads the turn (`Moment`) and what earlier sources offered, and returns its lines plus any writes that
  use up a cap or mark a plan asked, which run only once the turn is stored. Add a note there, not in
  `_assemble`.
- Ask a small model the same question several times with `loops/reads.py` `read_times` (each failed or
  unreadable read is None) and count agreement with `core/agreement.py` (`READS`, `unanimous`); a
  feature states what a failed read means for it (no agreement, or try the batch again later).
- Record a decision through `loops/record.py` (`Recorder.decide(key, detail, reason=...)`; in the turn,
  `_decide(c, t, ...)`), never by building `Decision(...)` by hand. Code that looks a past decision up
  matches its key (`decided_since`, `Decision.has_key`), never its reason text; decisions from before keys
  match by how their reason begins.
- Read the wall clock only through `core/clock.py` (`utc_now`, `local_zone`, `named_zone`). A test enforces it.

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
- Settings are environment variables in `.env`: `COMPANION_MODEL`, `COMPANION_ROLEPLAY_MODEL`,
  `COMPANION_REFLECT_MODEL`, `COMPANION_FALLBACK_MODEL` (asked only when the judges' model refuses a
  call), `COMPANION_DAILY_CAP_USD` (default 10, `off` removes it), `COMPANION_DB`, `COMPANION_PACE`,
  `COMPANION_SPLIT`, `COMPANION_LISTEN`, `COMPANION_INITIATIVE`, `COMPANION_MOOD`, `COMPANION_RESAMPLE`,
  `COMPANION_ROUTE_INTIMATE`, `COMPANION_RELEVANCE`, `COMPANION_EMBED_MODEL`, `COMPANION_BACKUP_DIR`, `COMPANION_TALKER_FALLBACK`, `COMPANION_CONSOLIDATE`, `COMPANION_PROMISES`, `COMPANION_LORE`, `COMPANION_REMINDERS`, `COMPANION_PROMPT_OVERRIDES` (try another prompt version without shipping
  it) and `COMPANION_CHARACTER` (a character sheet laid over the persona, `companion/characters.py`). The
  table is in `README.md`. They are read once into `companion/settings.py` (`Settings`, one row per switch in
  `SWITCHES`); the startup line is printed from it. A new switch is one row there.
- The console shows INFO; `data/logs/companion.log` (rotating, not committed) keeps DEBUG with timings
  per stage and the full text of what was said. Secrets are scrubbed by value (`logsetup.py`), and
  `httpx` stays at WARNING because its URLs carry the bot token.
- Never log or print the Telegram token. Telegram errors carry no URL (`TelegramError`).
- Restart with `just restart` in a terminal the owner can see, never as a hidden background job or under a
  timeout (it runs the bot in the foreground). It stops the old process first. Two bots on one token fight over updates. After a
  restart, confirm the "up as" line shows the new prefix and persona.
- A reply the user never received is marked undelivered and left out of what the model reads.
- Replies are held to feel typed: `COMPANION_PACE` is off, quick, natural (default) or slow.
  Set `off` when timing a run by hand. Commands are never held.
- A long, plain reply is sometimes sent as two or three messages (`COMPANION_SPLIT`, on unless `off`).
  The ledger and the history keep it as one reply, so the model never sees the splitting. Cuts fall at
  sentence boundaries only, and a reply with quoted speech (roleplay) is never split (`core/split.py`).
- A plain message that arrives while the previous one is still being answered (written or held)
  replaces that answer, and the dropped reply is marked undelivered, so the new reply sees both
  messages. Commands never supersede. The poll offset moves past a message when it is queued, so a
  restart can lose one that was queued but not answered.
- Things they said about their near future are recorded as open loops (`core/openloops.py`), and a
  pure gate (`core/initiative.py`) decides every 15 minutes whether to reach out. It only runs in
  shadow mode: it drafts and records `would send` and sends nothing (`COMPANION_INITIATIVE`, `off` to
  disable). Read it with `uv run companion initiative`. Only firm plans about their own life become loops
  (labels, not prompt rules); its kind sets the time (follow_up the morning after, celebrate on the
  day, encourage early that morning); a loop they settle themselves is closed as resolved, and after an
  unanswered live reach-out it waits 72 h, after two it waits for them to write first.
- When they say they are stepping away now ("shower time", "brb"; `system/away`, read beside any real,
  not serious turn) and then stay quiet at least twice as long as that and an hour, the 15-minute tick drafts
  one light nudge (`core/nudges.py`, `system/nudge-draft`): one per time away, never in quiet hours, never
  after a goodbye, gone after six hours, at most two a day, and any message from them cancels it. Shadow
  only, under `COMPANION_INITIATIVE`; read it with `uv run companion initiative`.
- A due open loop is also brought up when they next write (J15, `pick_note`): one note on a casual turn,
  at most one a day, each loop offered at most twice, never a sensitive one; the loop is then marked
  asked so it is never also a reach-out. A firm plan for later today becomes a note-only loop, due three
  hours on, and is never a reach-out The open-loop pass keeps its own bookmark (`open_loop_runs`): a failed call is read again
  next pass, and a batch that fails three times is let go with the reason logged.
- Each message outside a scene is read for how serious it is before the reply, and code adds a
  listening note (`core/listening.py`). `COMPANION_LISTEN=off` turns it off. Acute messages (severity 3)
  get no note and there is no crisis path yet. The same judge labels a message rude to the companion (a one-turn note for a
  cool reply) and a request to remember something; then a small model looks the topic up across every
  belief and the finds ride that turn's system block (`core/recall.py`). Sensitive (held) memories are
  in the card only on turns rated severity 1 or more; the beliefs the card has no room for are logged once
  per turn. A one-day moment of daily life (an event labelled daily and surface by the memory map) leaves
  the card a week after it was last mentioned; it stays in memory.
- How they want to be referred to is a setting (`companion address --set`) pinned after the clock on
  every turn. Until memory knows their name, a note on a casual turn (at most daily) asks for it, and their
  answer is stored as a belief quoting their words (`core/basics.py`, J48). Each memory is labelled
  with the part of their life it is about and how personal it is (`system/memory-map`, after each memory
  pass); code picks the thinnest part fine to ask about and, on a casual turn at most daily, only logs it
  (shadow, `core/knowing.py`). `uv run companion map` shows the map and the picks. When their own words
  touch a basic fact without giving it (age, work, who they live with, where they live; three agreeing reads
  of `system/basics-hook`), code checks memory with `system/basics-known` and, at most once a day and twice
  per basic, logs whether it would ask (the hook, `core/hooks.py`, shadow beside the turn).
- Which memories bear on the moment is looked up before the reply (ADR 0018, `core/relevance.py`,
  `COMPANION_RELEVANCE` on by default): their message (with its last reply) is embedded, and only when the
  closest memory they may see scores 0.42 or more does a small model pick up to three; at most two picks not
  already on the card reach the talker in `notes/relevant`. Outside scenes, 3 s limit. `shadow` runs it
  beside the turn and only logs it; `off` stops it.
- A message is answered at most once: Telegram updates are recorded before the turn runs.
- The database and the character sheets are snapshotted at every start (before migrations) and daily
  (`companion/backups.py`, J36), each copy checked; the newest 7 daily and 7 others are kept in
  `data/backups/` (`COMPANION_BACKUP_DIR`). `companion backup --restore FILE` refuses while the bot runs,
  keeps the current database first, and replaces nothing unless the copy passes its check.
- A mood that carries (ADR 0016, `core/mood.py`): each message adds effects to cozy, tender or playful in an
  append-only table, the mood is worked out from them when read, and only what the user did can move it
  (no source for silence, goodbyes, gaps or failed calls). `COMPANION_MOOD` is shadow, on or off;
  `uv run companion mood --replay 7` rebuilds it over past messages from the same rules.
- When a small topic has run its course (a short answer right after it asked something, read by its
  own judge `system/topic-spent`, never the listening judge), one note says to react briefly and move on
  (`core/topics.py`): to a plan of theirs offered that turn, else their day or evening, and late at night a
  thought of its own. At most once in ten of their messages, casual turns only, never past a question.
- A talker that errors is answered by its fallback model at once, and one still silent after 10 s
  has the fallback asked too, the first answer sent (`models/fallback.py` `TalkerFallback`, J21). The
  reply carries the model that wrote it, and every check runs on it as usual. Talker calls time out at 25 s.
- Memory tidies itself only where a judge matched the owner's own review (ADR 0019,
  `core/consolidate.py`): at 04:00 each memory a week old is read three times; a faded passing moment
  read so three times is closed, and out of date or overstated findings become questions for the owner.
  When the memory pass writes a new memory, the nearest existing one (by embedding, at 0.55 or more) is
  read as a pair three times; read as the same, the new quote becomes evidence on the old memory instead;
  read as a conflict (replaces or contradicts) all three times, it is a question for the owner, who keeps
  one or both (J11). Memories about one thing (one moment split into pieces, one interest restated) are grouped
  three times each night for the last two days (`system/memory-group`, `core/merging.py`; `companion memory
  group` for the whole store); each agreed group, with one wording that keeps every detail
  (`system/memory-merge`), is a merge question in `memory review`, and a conflict between two pieces of a
  pending merge is held back. `COMPANION_CONSOLIDATE` is shadow (log only) unless `on` or `off`. Nothing is merged
  automatically. `companion memory review` asks the owner the questions the check raised; `companion merge`
  merges by hand.
- When a short question of theirs invites a guess about them ("you know what time it is?"), its own judge
  says so, the recall look-up picks what may fit (never sensitive), and one note asks for a single
  playful guess as a question (`core/guess.py`, J16). It never guesses unasked.
- The companion's own lore lives in its views (ADR 0020): after each memory pass a small model labels each
  new view of its own as taste, stance, rule, self or lived (`system/lore-label`, `core/lore.py`); only a
  taste is lore, a lived claim never is; `companion lore` lists the tastes. On an ordinary turn (not
  serious, not a scene, not a goodbye) code embeds their message and shows it at most two of its tastes
  at 0.3 or more, as the words it said (`notes/lore`, `COMPANION_LORE` on, shadow or off). Next: a
  consistency check on new tastes.
- Things they name are matched in shadow (fetch on mention, `core/names.py`): after each memory pass a
  small model lists the names in new memories with the other words for each (`system/memory-names`), and
  on every ordinary turn code matches their message as whole words and logs the memories about each name
  that the card left out. Nothing reaches the talker; `companion names` shows the list and the count.
- The promises the companion makes in its own replies are read in the open-loop batch (J12,
  `core/promises.py`, `system/promise-read`): a model labels standing or once and a word it said it would
  stop using; code keeps one only if its quote is in that message, said for real, not hedged and forward
  looking. Shadow only (`COMPANION_PROMISES`, `off` to skip): recorded and listed by `companion promises`,
  never shown to the talker yet.
- Reminders they ask for are live (J50, `core/reminders.py`, `loops/reminders.py`), one-off only. A
  message with reminder words, or the answer when it just asked when, is read by `system/reminder-read`
  into their words for the thing and the parts of when; code works out the time in the machine's named
  zone (`named_zone`, so a time after a clock change keeps its wall time) and asks instead of guessing (a
  bare "at 8" with both still ahead, "next friday", a time gone, past sixty days, a repeating one). One
  note says it was set, with the time code worked out, or what to ask, or that one was cancelled. Every
  minute due ones are claimed once, written by the everyday talker with `system/reminder-send` as the tail,
  drawn once more on a code-check fail, and sent; their words go out marked when the talker fails or the
  cap is reached. A pretend scene holds them until it ends; one missed while the bot was down by over two
  hours is let go. A check-in with no time is set at a time picked once between 4 and 8 pm and confirmed
  only as the part of the day ("Thursday evening"). `companion reminders` lists them, `--cancel ID`
  drops one; `COMPANION_REMINDERS=off`.
- Evals run on the plain persona by default; the owner's character only as a labelled second check.
- Replies are checked before they are sent (`core/recheck.py`): on an ordinary turn (not serious, not
  a scene) an em dash, an AI disclaimer nobody asked for, the clock line or a tag copied from the system
  block, the stock "that sounds X, especially when" line and the stage direction "a beat", by code, and a joke bolted onto an ordinary
  message by the quip judge; in a scene or on a serious turn only the code checks. On a fail the same model is asked once more
  and the second reply goes out whatever it is; the first is kept in the decision detail. Nothing is ever
  edited, and an empty reply is drawn once more instead of a silent turn. `COMPANION_RESAMPLE=off` turns
  it off.
- Which talker answers is chosen in code (`core/floor.py`, ADR 0017): the roleplay talker for a pretend
  scene, or for intimate talk when `COMPANION_ROUTE_INTIMATE=on`, unless the listening judge reads the turn
  as age-coded or could not read it (a fallback model's reading counts as unread). That floor is code, not a
  setting. A held turn gets a note, its reply is read by an intimate check and redrawn (the last draw sees
  only their message), and if all read intimate nothing is sent; no reply is written by code. The roleplay
  talker also sees the character sheet's `## In roleplay and intimate moments` section; the everyday one
  never does. A `## Scene reminder` at the end of that section is sent after the history on roleplay
  turns (`TalkerRequest.tail`), where it weighs most; its words live in the private sheet. "Scene" means only a pretend scene in progress (the frame judge's label).

**Working with the owner**
- Plain English, short, and say what changed and what it was measured on. Lead with what matters.
- "Wait" and "hold" mean do nothing yet. A question is not a request to build.
- Ask before spending beyond a cap, changing the live persona or model in a way that is not a
  reversible measurement, or deleting anything. Decisions the owner has parked stay parked.
- Never run filesystem-wide searches (`find /`, `grep -r` from `$HOME`). Scope to this repo.
- Subagents get the same rules in their brief, including the no-global-search rule, and they are
  read-only unless the task says otherwise.
