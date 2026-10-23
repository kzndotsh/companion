# Turn stages, a feature shape and a feature-first layout (design sketch)

Design only: nothing here is built. It joins two proposals from the architecture audit of 2026-10-23,
splitting the turn into named stages and sorting the code by feature, because the folder layout should
come out of what a feature is, not before it. For the owner to read before any code moves.

## Why

One feature today lands in many places. The brush-off check (2026-10-23) touched the floor module, the
routing function and its return tuple, `_assemble`, `Moment`, the notes list, the manifest, the prompts
README and two changelogs. Reminders live in eight folders. Measured on 2026-10-23:

- `loops/fast.py` is 1,020 lines; `_handle_turn` runs every stage inline.
- Their message is stored in four places: three error paths (as real) and the success path.
- `Conversation` has 21 fields, the modes as plain strings.
- An independence contract over `loops.*` finds 70 imports from one loops module into another.
- 28 module names exist in both `core/` and `loops/`.

## 1. The turn as named stages

Each stage takes what the stages before it produced and returns its own result. A typed value per
stage, not one bag of optional fields, so a stage cannot read something not yet made.

```python
Arrived    (session, turn, now, text, prior, in_scene)          # load
Heard      (Arrived, labels | None, reaction | None)            # listen: ack + listening judge
Routed     (Heard, talker, held, brushed, read)                 # route: floor, explicit lead, brush-off
Looked     (Routed, Lookups)                                     # look: side by side, one deadline
Assembled  (Looked, request, card, notes.after)                 # assemble: card + notes, tail
Answered   (Assembled, reply, frame outcome, reaction)          # talk + check: talker, recheck, floor
Stored     (Answered, said, sent)                                # persist: user message, reply, records
```

`_handle_turn` becomes a short driver:

```python
async def handle(c, session, text, channel, now) -> Outcome:
    a = arrive(c, session, text, now)
    async with their_message(c, a, channel) as keep:   # the one place it is stored
        h = await listen(c, a)
        if h.reaction_only:
            return keep.reaction(h)
        r = await route(c, h)
        lk = await look(c, r)
        asm = assemble(c, lk)
        shadows(c, asm)
        ans = await talk_and_check(c, asm)
        return keep.reply(ans)        # persist + after-writes + name capture
```

`their_message` stores the message exactly once: on success with the frame the judge resolved, on any
exception as real (today's behaviour), then re-raises. The chaos test already checks "stored once"
under random judge failures, and replay MATCH checks the request is unchanged.

Stages live in `turn/stages/`, one module each, each under 450 lines (the file cap test).

## 2. What a feature is

Most features are a few of the same five parts. A feature declares the parts it has:

```python
@dataclass(frozen=True)
class Feature:
    name: str
    switch: Switch | None                          # its row in SWITCHES, if it has one
    look: Callable[[Moment], Awaitable[Found]] | None = None   # before the reply, under the deadline
    note: NoteSpec | None = None                   # a line for the system block
    shadow: Callable[[Moment], Awaitable[None]] | None = None  # beside the turn, logged only
    after_memory: Step | None = None               # a step after each memory pass
    nightly: Step | None = None                    # a step at 04:00
    command: Command | None = None                 # its `companion` subcommand
```

`FEATURES` is one tuple in `features/__init__.py`. The turn iterates it: look-ups run side by side
(today's `look`), notes go to the arbiter, shadows to `_beside`. Adding a feature is one folder and one
line in `FEATURES`, no edits to the turn, `Conversation` or `Lookups`.

Not every feature fits. Routing (the floor, brush-off, explicit lead), the recheck and the listening
judge are the turn itself, and stay in `turn/`. Forcing them into `Feature` would hide the safety
floor behind a registry; it should stay readable in one file.

## 3. Notes declare their order and their budget

```python
@dataclass(frozen=True)
class NoteSpec:
    slot: Literal["context", "ask", "rule"]   # context: what it knows; ask: a question to put; rule: how to answer
    after: tuple[str, ...] = ()               # notes it reads (today's so_far["check-in"] etc.)
    tail: bool = False                        # sent after the history (owned-it)
```

The arbiter orders notes by `after` (checked when the module loads, so a bad order fails at start, not
silently) and enforces a budget: at most one `ask` note a turn (the check-in, the name question, a due
plan, "move on" and an invited guess all ask something today and only some of them know about each
other). `context` and `rule` notes are not capped yet; measure the card first.

## 4. Folders by feature

From the audit's layout, with two changes marked.

```
src/companion/
  kernel/      shared pure types and tools: types, clock, agreement, spend, history, frames
  judges/      the Judge spec and runner (today's loops/ask.py)
  turn/        the reply path: stages/, notes arbiter, request, prefix, sections, split, pace,
               recheck, floor (routing and the safety floor stay here, see 2)
  memory/      the belief engine: extract, verify, card, freshness, relevance, recall,
               consolidate, merging, worth, context
  features/    one package each: logic.py (pure), run.py (effects), store.py (its queries),
               cli.py, README.md (its entry from docs/features.md)
               reminders, episodes, openloops (initiative, nudges), lore, mood, names, promises,
               guess, topics, basics, hooks, knowing, address, habits, callbacks ...
  adapters/    models, telegram, embeddings, sqlite (db, ledger, decisions, turns, migrations/)
  app/         daemon, settings, backups, characters, logsetup, cli entry
  evals/
  prompts/     stays central: manifest, immutable versions, name@version, overrides
```

Changed from the audit's sketch: floor and recheck sit in `turn/`, not in features (see 2); each
feature's `README.md` replaces its entry in `docs/features.md`, which then becomes an index.

## 5. Contracts that keep it that way

Checked on 2026-10-23 that the pinned import-linter (2.15) runs wildcard contracts and that one does
break on today's code (`companion.loops.*` independence: 70 cross-imports found).

1. Pure stays pure: `companion.features.*.logic`, `companion.kernel` and `companion.memory` (its pure
   modules) may not import `adapters`, `turn`, `app` or any `run`.
2. Features do not import each other: `independence` over `companion.features.*`. What one needs from
   another comes through `kernel` types or the turn's `Moment`.
3. Direction: `app -> turn -> features -> memory -> judges -> kernel`, as a `layers` contract;
   `adapters` only below `app`, `turn` and the `run` modules.
4. Only `adapters.sqlite` imports `sqlite3` (today's rule, renamed).

## 6. Order of work, each step on its own with the suite, the chaos test and replay MATCH

1. Stages in place: split `_handle_turn` into `loops/turn_stages/` modules with the typed stage values
   and `their_message`. No folder moves. Biggest win for the least churn.
2. `NoteSpec` and the arbiter: declare order and slots on today's `SOURCES`, add the one-ask budget.
   Measure on recorded turns that pile up asks, since the budget changes what the talker is sent.
3. `Feature` and `FEATURES`: convert two features (lore, reminders) to prove the shape.
4. Pilot the layout with reminders: a codemod moves its files and rewrites imports, contracts added,
   replay MATCH on recent turns. If it reads better, one feature per commit after that.
5. `kernel/`, `adapters/`, `app/` last, as pure renames, listed in `.git-blame-ignore-revs`.

Steps 4 and 5 are churn: hundreds of import edits and conflicts for any session working in `core/` or
`loops/` at the time. Do them when nothing else is in flight.

## Questions for the owner

1. Start with step 1 (stages in place, no moves)?
2. The one-ask-per-turn budget in step 2 changes replies. Fine to measure and ship it?
3. The full folder move (steps 4 and 5): worth the churn, or stop after step 3?
4. Found by the chaos test: a turn the floor holds, whose replies cannot be read (the judge model down),
   sends nothing (ADR 0017: doubt never sends). Keep, or send a plain non-intimate line written by the
   everyday talker with only their message?

## Progress

- 2026-10-23, step 1 in part: the stages are modules (`loops/hear.py`, `route.py`, `assemble.py`,
  `talk.py`, `beside.py`, `persist.py`), and their message is stored in one place by a guard around the
  whole turn, which also fixed a turn whose look-ups or card failed losing it. `loops/fast.py` went from
  1,044 to 224 lines. Left of step 1: the typed stage values (`Arrived`, `Heard`, `Routed`, ...); today the
  stages still pass loose arguments.
- 2026-10-23, step 1 finished: each stage returns a typed value (`Listened`, `Routed`, `Answered`) and owns
  its stop-on-error; the driver reads as the stages; `loops/fast.py` is 145 lines.
- 2026-10-23, step 3 begun: `Feature` (look and note so far) in `loops/features.py`; lore and reminders
  declare theirs in their own modules and are registered in `FEATURES`. Next: the after-memory, nightly
  and command parts, then more features, then the layout pilot.
- 2026-10-23, step 3 continued: `Feature` also carries steps after a memory pass, and the registry moved
  to `loops/registry.py`. Ten features declare their parts (memory map, names, context, worth,
  relevance, recent times, topic-spent, guess, lore, reminders); the memory pass runs all its after-steps
  from the registry; the notes order is one named list (`ORDER`) checked at load. `loops/notes.py` went
  from 708 to 479 lines. Not in the shape yet: the reminder delivery tick (one user) and commands (with
  the layout pilot). Left in `notes.py` as notes of the turn itself: listening, rude, repair, owned,
  recall, check-in, mood, hold, brush-off, the name question, the map pick and due plans.
- 2026-10-23, step 4 piloted with reminders: `src/companion/features/reminders/` holds `logic.py`, `run.py`,
  `store.py`, `cli.py` and its `README.md`; tests in `tests/features/reminders/`; moved by a script with
  `git mv` and import rewrites. Three new import-linter contracts (feature logic pure, features
  independent, only a feature's store touches sqlite) all kept. Prompts and the migration stayed central.

