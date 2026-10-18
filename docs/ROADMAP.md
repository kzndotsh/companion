# Roadmap

Written 2026-10-16, refreshed 2026-10-18. This is the one place that says what we are doing, in what order, and why.
Update it when something ships, when a measurement changes the plan, or when a decision is made.
It is allowed to be wrong, but it must never be stale. The work items themselves live in `TODO.md`;
the Now, Next and Later sections below say why they are in that order.

How it fits with the rest of `docs/`:

| Where | What goes there |
|---|---|
| `TODO.md` (repo root) | the cards: todo, doing, done, canceled and the backlog. Pull work from there |
| this file | the principles, the current state, the measured facts and the reasoning behind the order |
| `docs/adr/` | decisions, once made, with the reason |
| `docs/inbox/` | ideas and questions that are not yet anything. Nothing there is a task |
| `docs/research/` | audits and studies. Read-only background. Local only: git-ignored, not committed |
| `src/companion/prompts/CHANGELOG.md` | every version of every prompt, and code changes to what the model is sent (card, clock, notes, which model answers) |
| `src/companion/prompts/README.md` | every prompt, and how a request is assembled |
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

## Where we are (2026-10-18)

Live: persona **v26**. Everyday chat on **GPT-6 Luna**, pretend scenes on **DeepSeek V4 Flash**,
judges and memory extraction on **Claude Haiku 5.5**. Persona v28 (the quoted sample phrases removed)
is measured and waiting for the owner's say. 11 ADRs, 70 public eval fixtures plus the private
recorded ones, and about 650 tests with strict lint and types.

Built and working:

- **Memory.** Quoted beliefs with frames and times, freshness and "older, may be out of date",
  confirmation by restatement, the companion's own views with gates and approval, the rejected list
  so retirements stick. Scene and romantic behaviour in the chat and refusals said in reply to a push
  are not recorded. Flags retire only the views they implicate.
- **Reply path.** No thinking on the talker. Small judges run before the talker: ack (react instead of
  replying), frame (real, play, story, what-if), and listening (how serious it is, what they are
  doing, whether it is medical). Code turns the labels into notes in the system block: a listening
  note by severity, a length note for short statements, a scene note, habit notes. The reaction judge
  and the habit check run beside or after the reply. A scene is answered by a different model.
- **Delivery.** Replies are held to feel typed, long plain replies are sometimes sent as two or three
  messages, and a new message that arrives before the last answer is out replaces it. A reply
  Telegram never delivered is recorded as undelivered and left out of what the model reads.
- **Initiative.** Things they say about their near future become open loops, and a pure gate decides
  every 15 minutes whether to reach out. Shadow mode only: it drafts and records, and sends nothing.
- **Prompts.** Every prompt, the persona included, is versioned text under `src/companion/prompts/`
  with a manifest, one changelog and tests. Decisions log `name@version`. `companion prompts` lists
  them and `companion replay <turn_id> --show-prompt` prints what a turn sent.
- **Observability and cost.** A rotating debug log with per-stage timings, a spend ledger, and a daily
  cap ($10 by default).
- **Evals.** Scripted and recorded fixtures, deterministic and judged checks, an empathy rubric check,
  variants by persona, model, card, history window, reasoning, length note and listening note, a spend
  cap, a runner that survives a failing provider, and opt-in live tests that calibrate each judge.
- **Feedback.** `/flag` and `/fav`, listed with `companion flags` and `companion favorites`, each
  replayable with `companion replay`.

Measured facts that drive the plan:

| Finding | Number | Where |
|---|---|---|
| Luna leads everyday chat | 59/64 on the public fixtures, DeepSeek 49/64 | prompts CHANGELOG |
| DeepSeek keeps a scene going | 76% of escalating turns, Luna 52% | prompts CHANGELOG |
| Notes in the user's message leak into replies | 7 to 8 of 48, now 1 of 48 in the system block | prompts CHANGELOG, assembly |
| The memory block in the user's message made it recite | held facts surfaced 8/24, now 0/24 | prompts CHANGELOG, assembly |
| Diagnosing a small mishap (v25 made it worse than v22) | pancakes fixture 9/30, v26 30/30 | `evals/CHANGELOG.md` |
| The listening judge labels severity correctly | 59 of 60, and no serious message read as trivial | `evals/CHANGELOG.md` |
| A health note makes it point to a doctor | medication fixture 0/20 to 19/20 | `evals/CHANGELOG.md` |
| Cheesy quips on a real flagged turn were not copied from the history | shorter history did not help; a per-turn note took it from 16/30 to 29/30 | `evals/CHANGELOG.md` |
| A shorter history window loses what is beyond it | 12/12 in view, 0/12 out; the card updates only after 90 s quiet | `evals/CHANGELOG.md` |
| Trivial vents get only a restated detail | 0/20 on the empathy check; unsolved | `evals/CHANGELOG.md` |
| Only a "do it like this" quoted sample is parroted | "scattered" 5 of 6 on the mood fixture to 0 without it | `evals/CHANGELOG.md` |
| A model finds a real afterthought rarely | about 1 reply in 20; open loops about 8 in 3 days | `evals/CHANGELOG.md` |
| Scene voice does not carry over to Luna | 20/20 plain after a scripted scene | `evals/CHANGELOG.md` |

## Housekeeping that can stop the bot

- [ ] **Check the OpenRouter balance.** The bot goes quiet at zero, and the daily cap is $10.
- [ ] **Revoke the Telegram bot token** in BotFather. Parked by the owner; do not raise it again until
      asked.
- [ ] **Triage `docs/research/2026-10-16_sapphire-audit/`.** It is untracked and unread (`TODO.md` H3).

## Now

Each item ends with the thing that tells us it is done. The cards are in `TODO.md`.

1. **Watch the live setup in real chat.** Flag and favourite as usual. *Done when:* a week of marks
   shows whether the scene model helps, where the voice changes at the boundary hurt, and how the
   listening note and the pacing feel (D1).
2. **Hand labels for replies.** The owner marks replies from the review sheet in batches of ten
   (`evals/local/`); items 1 to 10 are in. *Done when:* the judges are calibrated against the marks and
   the trivial-vent question has an answer (T14).
3. **Prompt experiments** from the guides review (T15): ship or hold persona v28, a trimmed persona,
   positive rewrites of the notes, a stock-phrase note. *Done when:* each is measured and decided.
4. **A week of shadow mode** for open loops. *Done when:* the owner has read `companion initiative` and
   the caps are set. Going live also needs outcome recording and a slow re-probe.

## Next

- **A crisis path for acute messages** (R16, on hold). The listening judge already labels them and does
  nothing. Needs the owner's design.
- **A rule and a test against sexualized child-coded roleplay,** since the scene model is the weaker
  guard. Needs the owner's design.
- **A language guard** that regenerates once when a reply uses a script the user has not.
- **Pacing ADR** (T2), **provider routing for DeepSeek** (T8), the two DeepSeek-only gaps (T4, T5).
- **Looking up older messages** when the user says "remember" (R2), **recording the lore it invents**
  (R3), **reactions** beyond acknowledgements, **calibrating the view gates**, and **eval tooling**
  (favourites to fixtures, a gate on synthetic-only data).
- **History hygiene:** a flag does not always say which reply it is about, so dropping flagged replies
  was tried and reverted (T9).
- **Cache:** the 40-message window slides each turn, so the history is never cached.

## Later

- A persona-change gate: hash-bound proposals, paired evaluation, a drift cap per revision,
  rollback (the shape in the Alicization audit).
- Mood and style profile, belief confidence from independent days of evidence, game state (whose
  turn, what was just asked).
- A seconds-level afterthought, if a better source than a model's guess appears. A prototype found
  almost no real material.
- Voice, if ever: commit only what was heard.
- Productising: onboarding, an adults-only gate and consent record, provider and data policy,
  billing. No audited project has a working consent layer, so this is ours to design.

## Decisions needed from the user

1. **Persona v28:** ship it? It removes one parroted phrase at no measured cost.
2. **Pacing (T2):** evidence-based, the dial, or both? How much friction is the default?
3. **Intimacy limits and child-coded roleplay:** where the character's own pace ends and the model's
   hard limits begin, how a refusal is shown, and what happens with child-coded sexual roleplay.
4. **A crisis path** for acute messages.
5. **Provider routing (T8):** sort by latency, or pin a provider list.
6. **Going live with reach-outs:** after a week of shadow mode, with the caps (23:00 to 08:00 quiet,
   one a day) confirmed.
7. **The body and appearance question** (inbox, parked since the start).

## Parked in the inbox

Not tasks. Read each before acting on it.

- Body and appearance questions
- Whether the "letting them go" rule earns its place
- Reacting to messages beyond acknowledgements
- When the user reacts to its messages
- Split messages and follow-ups (split is built; the afterthought is parked)
- Keeping track of the lore it invents
- Looking up older messages when asked to remember
- Real messaging datasets for texting norms
- Restating the user's point (research and measurement)
- Prompting and humanizing guides (reviewed; the experiments are T15)

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
