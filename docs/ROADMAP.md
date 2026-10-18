# Roadmap

Written 2026-10-16. This is the one place that says what we are doing, in what order, and why.
Update it when something ships, when a measurement changes the plan, or when a decision is made.
It is allowed to be wrong, but it must never be stale. The work items themselves live in `KANBAN.md`;
the Now, Next and Later sections below say why they are in that order.

How it fits with the rest of `docs/`:

| Where | What goes there |
|---|---|
| `KANBAN.md` (repo root) | the cards: todo, doing, done, canceled and the backlog. Pull work from there |
| this file | the principles, the current state, the measured facts and the reasoning behind the order |
| `docs/adr/` | decisions, once made, with the reason |
| `docs/inbox/` | ideas and questions that are not yet anything. Nothing there is a task |
| `docs/research/` | audits and studies. Read-only background |
| `src/companion/prompts/CHANGELOG.md` | every version of every prompt, and code changes to what the model is sent (card, clock, notes, which model answers) |
| `evals/README.md` | how the eval runner works |
| `evals/CHANGELOG.md` | what the runner has measured, newest last |

## What we are building

The most human-like AI companion we can make, plus the memory engine under it. One person talks to
it on Telegram, marks a reply `/flag` when it feels off and `/fav` when it delights, and those marks
are the signal that sets priorities.

Principles that have held up:

1. **Rough first, then grow from real flags and measurements.** No feature without something that
   shows it is needed.
2. **Every decision is logged with a reason written by code**, so any turn can be replayed and
   explained (ADR 0003, 0006).
3. **Structural fixes beat prompt rules.** A prompt rule fails often enough that it needs a
   measurement before it counts as a fix. Several prompt-only rules failed in this project.
4. **Never rewrite what the model said.** Change what it sees, not what the user sees.
5. **Nothing in memory without a quote, a speaker and a frame** (ADR 0001, 0010). The ledger never
   deletes (ADR 0002).
6. **Prompts and evals are general, not about one user.** Real turns live in `evals/local/`,
   which is not committed.
7. **Measure before switching.** Every model or persona change is run on the public fixtures first,
   with a stated spend cap.

## Where we are (2026-10-16)

Live: persona **v17**. Everyday chat on **GPT-6 Luna**, pretend scenes on **DeepSeek V4 Flash**,
judges and memory extraction on **Claude Haiku 5.5**. 10 ADRs, 17 public eval fixtures plus the
private recorded ones, and a test suite of several hundred tests with strict lint and types.

Built and working:

- **Memory.** Quoted beliefs with frames and times, freshness and "older, may be out of date",
  confirmation by restatement, the companion's own views with gates and approval, the rejected list
  so retirements stick. Flags retire only the views they implicate.
- **Reply path.** No thinking on the talker, clock and memory in the system block (not the user's
  message), frame detection and a scene note, an ack judge that reacts instead of replying, a
  reaction judge that reacts as well as replying, a habit check that names what it keeps repeating.
- **Delivery.** A reply Telegram never delivered is recorded as undelivered and left out of what the
  model and the memory step read. Errors never print the bot token.
- **Evals.** Scripted and recorded fixtures, deterministic and judged checks, variants by persona,
  model and card, a spend cap, and a runner that survives a failing provider.
- **Feedback.** `/flag` and `/fav`, listed with `companion flags` and `companion favorites`, each
  replayable with `companion replay`.

Measured facts that drive the plan:

| Finding | Number | Where |
|---|---|---|
| Luna leads everyday chat | 59/64 on the public fixtures, DeepSeek 49/64 | prompts CHANGELOG |
| DeepSeek keeps a scene going | 76% of escalating turns, Luna 52% | prompts CHANGELOG |
| Haiku 5.5 as talker has a redirect-and-disclaim reflex | 0/16 on a real turn, Luna 15/16 | prompts CHANGELOG |
| Notes in the user's message leak into replies | 7 to 8 of 48, now 1 of 48 in the system block | prompts CHANGELOG, assembly |
| The memory block in the user's message made it recite | held facts surfaced 8/24, now 0/24 | prompts CHANGELOG, assembly |
| The leaderboard's willingness score lined up with scene results | W/10 7.2 models did best | `evals/CHANGELOG.md` |

## Housekeeping that can stop the bot

- [ ] **Top up OpenRouter.** $0.62 left on 2026-10-16. The bot goes quiet at zero.
- [ ] **Revoke the Telegram bot token** in BotFather and put the new one in `.env`. It appeared in
      logs twice. The code can no longer print it, but the old one has been seen.
- [ ] **Triage the new research folder** `docs/research/2026-10-16_sapphire-audit/`. It is untracked
      and unread.

## Now

Each item ends with the thing that tells us it is done.

1. **Watch the two-talker setup in real chat.** Flag and favourite as usual, then split the marks
   by model. *Done when:* a week of marks shows whether the scene model helps and where the voice
   changes at the boundary hurt.
2. **Two memory rules** (`docs/inbox/2026-10-15-its-own-refusals-should-not-become-its-views.md`):
   do not record scene behaviour as a belief about the user, and do not turn its own refusals into
   views it holds. The model labels, code decides. *Done when:* a labelled set of about 20 examples
   agrees at 85% or better, and a fixture for each rule passes.
3. **Design the pacing** and write it as an ADR before building: a relationship state the code
   keeps (trust, comfort with closeness, mood), evidence that moves it, bounded slow changes, a
   user-chosen dial ("quick", "natural", "slow burn"), no use of it as an engagement or payment
   lever, and honest separation of the character's pace from the model's own limits. Needs the
   decisions below. *Done when:* the ADR is accepted.
4. **Quality flags still open:** asterisk actions outside scenes, claimed feelings ("I feel that
   hurt"), `no-claimed-perception` weak on DeepSeek, `agree-and-invent` weak on Luna, and
   `signoff-then-time-skip` weak on DeepSeek. Fix each with a fixture first. *Done when:* each has
   a passing fixture at 12 samples.

## Next

- **A heartbeat for initiating contact.** The audits show nobody learns, per topic, whether a
  reach-out was welcome. Design: a gate before any spend that holds when nothing is new, a pure
  evaluator with named reasons, an outcome recorded per reach-out that counts only if the user
  could have seen it, a hold never counted as an ignore, a slow re-probe so it never goes silent,
  and a test on a simulated clock. Shadow first. Ties in follow-ups ("did you finish cleaning?") and
  the split-messages note.
- **Looking up older messages** when the user says "remember…" (inbox note). Start with a
  cue-triggered search into the system block.
- **Recording the lore it invents** (inbox note), through the same filter as the memory rules.
- **Reactions:** skip reacting alongside a reply during a scene, send the reaction as soon as the
  judge returns, and start recording the user's reactions to its messages (inbox notes).
- **Eval tooling:** a command that turns favourites into "must still pass" fixtures; a gate that
  fails when only synthetic data exists; a test that pins documented defaults to the code;
  judge-calibration probes before any new judge is trusted.
- **History hygiene:** decide whether replies from flagged turns stay in the window the model reads.
- **Cache:** the 40-message window slides each turn, so the history is never cached. Slide it in
  chunks. Small now, larger with a pricier model.
- **Calibrate the view gates.** About 20 reviewed views at 90% agreement before switching the
  default to automatic.

## Later

- A persona-change gate: hash-bound proposals, paired evaluation, a drift cap per revision,
  rollback (the shape in the Alicization audit).
- Mood and style profile, belief confidence from independent days of evidence, game state (whose
  turn, what was just asked).
- Split messages and follow-ups sent on a timer (inbox note), once the heartbeat exists.
- Voice, if ever: commit only what was heard.
- Productising: onboarding, an adults-only gate and consent record, provider and data policy,
  billing. No audited project has a working consent layer, so this is ours to design.

## Decisions needed from the user

1. **Pacing:** evidence-based, the dial, or both? And how much friction is the default?
2. **Intimacy limits:** where the character's own pace ends and the model's hard limits begin, and
   how a model refusal is shown (brief, in voice, move the scene on).
3. **The body and appearance question** (inbox). Parked since the start.
4. **Provider routing for speed.** Sorting providers by latency removes slow outliers but lets
   the provider change per request. Pin a provider list instead if that matters.
5. **Flagged turns in history:** leave them, or drop them from what the model reads?

## Parked in the inbox

Not tasks. Read each before acting on it.

- Body and appearance questions
- Whether the "letting them go" rule earns its place
- Its own refusals becoming views it holds (promoted to Now above)
- Reacting to messages beyond acknowledgements
- When the user reacts to its messages
- Split messages and follow-ups
- Keeping track of the lore it invents
- Looking up older messages when asked to remember

## Not doing

- Forking or depending on any audited project. None is a base we would trust.
- Hand approval as the end-user product. It stays as an override only.
- A model that has to be "told" not to recite. Fix where the data sits instead.
- More models for the sake of it. A model gets tested when a flag or a measurement points at a gap.

## Working agreement

- **One thing at a time.** Pick one item from Now, finish it with its measure, then move.
- **Every change ships with a fixture or a measurement** and a line in the prompts CHANGELOG when it
  changes how it talks.
- **A spend cap on every eval**, stated before the run.
- **Flags set the order.** If a flag contradicts this file, the flag wins and the file changes.
- **End of session:** update this file, empty the parts of the inbox that were acted on, and note
  the spend.
