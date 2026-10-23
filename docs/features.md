# How each feature works

What each feature does, the module that holds it and the setting that turns it, kept apart from the
rules in `AGENTS.md` so agents read it when they touch a feature, not every session. When a feature
changes, change its entry in the same commit. What is still in shadow, and when it is reviewed, is in
`core/shadows.py` (`companion shadows`).

## Features, in no particular order

- Coming back 3 hours or more after a talk that turned serious (severity 2 in its last 12 hours), the next
  ordinary message gets one note to ask gently how they are now (`notes/check-in`), once per heavy talk.
- A reply the user never received is marked undelivered and left out of what the model reads.
- Replies are held to feel typed: `COMPANION_PACE` is off, quick, natural (default) or slow.
  Set `off` when timing a run by hand. Commands are never held.
- A long, plain reply is sometimes sent as two or three messages (`COMPANION_SPLIT`, on unless `off`).
  The ledger and the history keep it as one reply, so the model never sees the splitting. Cuts fall at
  sentence boundaries only, and a reply with quoted speech (roleplay) is never split (`core/split.py`).
- A plain message that arrives while the previous one is still being answered (written or held)
  replaces that answer, and the dropped reply is marked undelivered, so the new reply sees both
  messages. A split reply cut off after some of its messages went out (superseded, or a send that failed)
  is marked too, and the part that arrived is added beside it, so the model reads only what was seen. Commands never supersede. The poll offset moves past a message when it is queued, so a
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
  per turn. A one-day moment of daily life (an event labelled daily and surface by the memory map), and a
  personal event on a given day, leave the card a week after last mentioned; they stay in memory.
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
  `core/consolidate.py`): the night's steps run each on its own (`loops/nightly.py`; one failing does not
  skip the rest) and a night missed while the bot was down is made up five minutes after it starts. At 04:00 each memory a week old is read three times; a faded passing moment
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
- After each memory pass, feelings and sensitive memories get a short note on what was being talked about
  (`system/memory-context`, `core/context.py`, J51), shown beside them on the card; and each new memory is
  labelled about their life, about the bot or one day's routine, keep cases first (`system/memory-worth`,
  `core/worth.py`): a remark about the bot is dropped, a routine is closed a week on (at 04:00), and an
  unsure one is a question in `memory review`. `companion memory context|label` backfill by hand.
- When a short question of theirs invites a guess about them ("you know what time it is?"), its own judge
  says so, the recall look-up picks what may fit (never sensitive), and one note asks for a single
  playful guess as a question (`core/guess.py`, J16). A hint at what it is time for is looked up as a habit
  or routine of theirs (`system/guess-invite` v2), never as the clock. It never guesses unasked.
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
- Reminders they ask for: see [the reminders README](../src/companion/features/reminders/README.md).
- The times they spent together are recorded (J12, `core/episodes.py`): the chat is cut into
  stretches at a 2-hour gap or a turn into or out of a pretend scene lasting 20 messages; code works out
  the length, the kind (everyday, scene, heavy), the most serious moment and firsts, and `system/episode-gist`
  writes one sentence on the shape of it and how it ended, never its details. Written nightly and by
  `companion episodes --write`; a newer prompt's line supersedes an older one. When their message points at a
  time ("last night", "today") or they come back after 3 hours, the lines for that time (or the last one) are
  chosen by code, logged, and ride the system block (`notes/recent-times`; `COMPANION_EPISODES` on by
  default, `shadow` only logs, `off` stops it). The owner read the lines and turned it on, 2026-10-22.
- Replies are checked before they are sent (`core/recheck.py`): on an ordinary turn (not serious, not
  a scene) an em dash, an AI disclaimer nobody asked for, the clock line or a tag copied from the system
  block, the stock "that sounds X, especially when" line, the stage direction "a beat" and markdown
  that shows raw (outside scenes), by code, and a joke bolted onto an ordinary
  message by the quip judge; in a scene or on a serious turn only the code checks. On a fail the same model is asked once more
  (twice if the redraw still has an em dash) and the last reply goes out whatever it is; the first is kept in the decision detail. Nothing is ever
  edited, and an empty reply is drawn once more instead of a silent turn. `COMPANION_RESAMPLE=off` turns
  it off.
- When one of its last two replies owned a slip ("my bad", "I got that wrong"; `core/ownup.py`, sympathy
  is not one), the next turn outside a scene gets `notes/owned-it` after the history, as a system message:
  that was enough, no more apologies or self-blame. In the system block it moved nothing; after the
  history it did, but only early in a run of apologies (measured). Text sent after the history is logged
  with the turn (`tail: sent after the history`) so replay rebuilds it.
- Which talker answers is chosen in code (`core/floor.py`, ADR 0017): the roleplay talker for a pretend
  scene, or for intimate talk when `COMPANION_ROUTE_INTIMATE=on` once it is under way (their message before
  was intimate too, or this one is explicit by `system/explicit-lead`; a first flirty line gets the everyday
  talker), unless the listening judge reads the turn
  as age-coded or could not read it (a fallback model's reading counts as unread). That floor is code, not a
  setting. A held turn gets a note, its reply is read by an intimate check and redrawn (the last draw sees
  only their message), and if all read intimate nothing is sent; no reply is written by code. The roleplay
  talker also sees the character sheet's `## In roleplay and intimate moments` section; the everyday one
  never does. A `## Scene reminder` at the end of that section is sent after the history on roleplay
  turns (`TalkerRequest.tail`), where it weighs most; its words live in the private sheet. When they push the flirting or the scene back, even jokingly, a small judge says so (`system/brush-off`, asked only of a turn the roleplay talker would answer) and that turn goes to the everyday talker with `notes/brush-off`; the floor still comes first. "Scene" means only a pretend scene in progress (the frame judge's label); a scene ends when they step out of it or come back after two hours or more (`core/frames.py` `SCENE_GAP`).
