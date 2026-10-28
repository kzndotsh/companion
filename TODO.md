# Todo

The work board and the plan: where we are, what we measured, what comes next, and the cards. Created
2026-10-16; the roadmap was folded in on 2026-10-19 so there is one file to keep current. The principles
are in `AGENTS.md`. Update this file when something ships, when a measurement changes the plan, or when a
decision is made; it may be wrong, but never stale.

**How to use it**

- A card is one line: `- [ ] ID title. note (tag)`. Move the line between sections to move the card.
- **Doing holds at most two cards.** Finish or move one before pulling another.
- **Todo is ordered.** Pull from the top.
- Every card that changes how it talks needs a fixture or a measurement, and a line in
  `src/companion/prompts/CHANGELOG.md` (a prompt version, or a code change to what the model is sent).
- Tags in the backlog say where we stand: **built**, **partial**, **new**. A card waiting on a review or a
  decision goes in **Waiting**; one parked by the owner or until a named trigger goes in **Parked**.
- IDs: `H` housekeeping, `T` ready work, `G` from the greenfield design
  (`docs/research/2026-10-15_greenfield-design.md`, numbered as in the review of 2026-10-16),
  `R` from the roadmap and inbox notes, `J` from the research walk-through, `LR` its own lore, `A` the audit
  synthesis, `D` and `Q` questions settled by watching or by the logs. Done cards keep their IDs.
- Items marked **needs decision** are blocked on an answer from the user.
- **One thing at a time.** Pick one item from Now, finish it with its measure, then move.
- **Every change ships with a fixture or a measurement** and a line in the prompts CHANGELOG when it
  changes how it talks.
- **A spend cap on every eval**, stated before the run.
- **Flags set the order.** If a flag contradicts this file, the flag wins and the file changes.
- **End of session:** update this file, empty the parts of the inbox that were acted on, and note
  the spend.

---

## Where we are (2026-10-25)

Live: persona **v46** (v41 plus that it can send reminders and check-ins when asked) with a private character sheet. Everyday chat on **GPT-6 Luna**, pretend scenes and
(when the operator turns it on) intimate talk on **DeepSeek V4.1 Flash**, judges and memory extraction on
**Claude Haiku 5.5** with a fallback model for calls it refuses, and a judge may read on its own model first
(`COMPANION_JUDGE_ROUTES`; the crisis judge reads on DeepSeek first). 22 ADRs, 110 public eval fixtures and
40 public crisis cases plus the private recorded ones, and about 1,460 tests with strict lint, types,
import layers and code rules.

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
- **Since 2026-10-18.** A mood that carries (ADR 0016: cozy, tender, playful, kept by code, shown only
  in behaviour; proposed, on for the owner, review 2026-10-29). A pinned line for how they want to be
  referred to, asked for on a casual turn until known, and kept from their own answer. Sensitive memories
  only on turns where they are sharing something. One resample when a reply fails a check (an em dash, a
  joke bolted onto an ordinary message, an AI disclaimer nobody asked for). Routing in code (ADR 0017):
  scenes and, when the operator allows it, intimate talk go to the roleplay model, above an age floor no
  setting changes; a held turn's reply is checked and redrawn, and never written by code.
- **Since 2026-10-19.** Persona v41 (picks for itself, keeps its view under pushback). In shadow: the
  nightly memory check and the same-memory check (ADR 0019), the map of what it knows about them (J48).
  Live: due plans brought up when they next write (J15), repair notes (J30), a topic-spent note, invited
  guesses (J16), an everyday standby (J21), daily backups (J36), the clock and notes in tags, and
  conflicting memories asked about in `memory review`.
- **Since 2026-10-20.** Its own tastes shown back when the moment touches them (ADR 0020, live). In
  shadow: promises it makes read from its replies (J12, `companion promises`), names matched against
  memory (`companion names`), and its views labelled taste, stance, rule, self or lived (`companion lore`).
- **Since 2026-10-21.** Reminders and check-ins they ask for, live (J50, `companion reminders`); from
  2026-10-26 also repeating ones and daily greetings, built and not yet measured.
  Memory review asks every question until quit and proposes merges of memories about one thing; feelings
  and sensitive memories carry a note on what was being talked about (J51); each new memory is labelled
  about their life, about the bot (dropped) or one day's routine (a week).
- **Since 2026-10-22.** Memories that bear on their message reach the reply when one is near (ADR 0018,
  live behind a gate). What the two of them did lately, when their words point at a time or they come back
  after a gap (J12, J49, `companion episodes`). A gentle check-in after a heavy talk and a gap. After it
  owns a slip, a note after the history says that was enough. A split reply cut off part way is remembered
  as the part that arrived.
- **Since 2026-10-23.** Intimate talk goes to the roleplay talker only once a message of theirs is
  explicit, and flirting no longer starts it; a push-back on flirting or a scene goes to the everyday
  talker with a note to drop it; a scene ends when they come back after two hours. One of its own
  emoticons is offered after the history on casual turns (`COMPANION_MARKS`, on by the owner's choice). A
  view stored firmer than its words is marked overstated and never installs itself. An invited guess finds
  their ritual (J16). The code is laid out as turn stages and one folder per feature, with a layer contract,
  one judge runner, a chaos test of whole turns, code rules as tests and a register of shadow features
  (`companion shadows`).
- **Since 2026-10-24.** What they said in the last 12 hours comes first on the card. After three question
  replies in a row a note asks for none (`notes/question-run`); in a game of questions they started, a note
  asks for the next one (`notes/question-game`). Their emoticon is named as theirs before its own is
  offered. A canned generic reaction is redrawn once (`system/quip` v3; its precision is in question, Q3).
  A hedged plan of theirs becomes a note-only loop (`COMPANION_HEDGED_PLANS`, loose). It asks which pronouns
  they use the way it asks a name. A lone short reaction in asterisks no longer starts a scene, and `/mode`
  says which talker answered. A stop answers what was already received before it exits. In shadow: reaching
  out for its own reasons (ADR 0021, review 2026-11-02) and the crisis path (ADR 0022, review 2026-11-04).
- **Since 2026-10-25.** The clock line gives the date. A calendar of occasions, live (`COMPANION_CALENDAR`,
  `companion calendar`): one note after the history on the first casual turn of the day for a warm US
  public or cultural day, the lead-up to a big one, or the relationship's month, hundred days or years;
  days of remembrance and contested days are left out. The judges stay on Haiku after a bake-off.
- **Delivery.** Replies are held to feel typed, long plain replies are sometimes sent as two or three
  messages, and a new message that arrives before the last answer is out replaces it. A reply
  the chat never delivered is recorded as undelivered and left out of what the model reads; a reply cut
  off part way is read as the part that arrived. On a stop it fetches nothing more and answers what it has,
  for up to 30 s.
- **Initiative.** All reaching out first is shadow: it drafts and records, and sends nothing. Three
  sources share one gate and its caps: a due firm plan of theirs (ADR 0015), a nudge after they stepped
  away and stayed gone, and its own reasons (ADR 0021: a time they keep, a thought, missing them, on
  learned hours, at the share of conversations `COMPANION_REACH` sets, `warm` by default, with a guilt
  check on every draft). At the first review (2026-10-24) the plan and nudge sources had drafted nothing.
- **Crisis path (ADR 0022), shadow.** A three-read risk judge reads messages the listening judge calls
  serious or that use crisis words, tells a literal risk from a joke and fails safe; code picks none,
  figurative, concern or urgent and logs what it would do (an in-character note, a fixed crisis-line
  message at urgent, 988 by default, a scene stepped out of, reach-outs held). `companion crisis --check`
  runs the public cases.
- **Prompts.** Every prompt, the persona included, is versioned text under `src/companion/prompts/`
  with a manifest, one changelog and tests. Decisions log `name@version`. `companion prompts` lists
  them and `companion replay <turn_id> --show-prompt` prints what a turn sent.
- **Observability and cost.** A rotating debug log with per-stage timings, a spend ledger, and a daily
  cap ($10 by default).
- **Evals.** An eval sample is made by the turn's own code (its notes, its request layout, its checks and
  redraws; `+raw` skips them), and every public fixture carries the live listening judge's reading as its
  labels, so results from before 2026-10-24 are not comparable with later ones. Noise bars, a spend cap, a
  runner that survives a failing provider, and opt-in live tests that calibrate each judge on any model
  (`COMPANION_LIVE_JUDGE_MODEL`).
- **Feedback.** `/flag` and `/fav`, listed with `companion flags` and `companion favorites`, each
  replayable with `companion replay`.

### Measured facts that drive the plan

| Finding | Number | Where |
|---|---|---|
| Luna leads everyday chat | 59/64 on the public fixtures, DeepSeek 49/64 | prompts CHANGELOG |
| DeepSeek keeps a scene going | 76% of escalating turns, Luna 52% | prompts CHANGELOG |
| Pretend scenes stay with the roleplay talker | the everyday talker preferred 13/56 and 11/56 by blind judges, stepped out of the scene in about 17 | `evals/CHANGELOG.md` (2026-10-24) |
| Warm turns stay on Luna | DeepSeek 73/96 against Luna 90/96 on warm public fixtures | `evals/CHANGELOG.md` (2026-10-23) |
| The scene reminder caused the escalation | went past their level 19/30 with the old reminder, 6/30 with "only as far as they take it" | `evals/CHANGELOG.md` (2026-10-24) |
| Notes in the user's message leak into replies | 7 to 8 of 48, now 1 of 48 in the system block | prompts CHANGELOG, assembly |
| The memory block in the user's message made it recite | held facts surfaced 8/24, now 0/24 | prompts CHANGELOG, assembly |
| Diagnosing a small mishap (v25 made it worse than v22) | pancakes fixture 9/30, v26 30/30 | `evals/CHANGELOG.md` |
| The listening judge labels severity correctly | 59 of 60, and no serious message read as trivial | `evals/CHANGELOG.md` |
| Haiku stays the judge model | bake-off across Haiku, Luna and DeepSeek on every graded judge: most gaps within noise; Luna and DeepSeek broke memory rules, Haiku's provider refused 7 crisis reads | `evals/CHANGELOG.md` (2026-10-25) |
| The crisis risk judge tells a risk from a joke | 40 public cases, three runs: no genuine risk missed, no joke raised; 39 of 40 exact after the level fix | `evals/CHANGELOG.md` (2026-10-25) |
| The canned-reaction judge over-fires | precision 35 to 55% against relabelled answers, not the 88% first measured; live it redrew 1 of 58 turns | `evals/CHANGELOG.md` (2026-10-25) |
| A health note makes it point to a doctor | medication fixture 0/20 to 19/20 | `evals/CHANGELOG.md` |
| A plain note makes it notice the day | Halloween named 0/12 with the date alone, 12/12 with a note; every day 6/6 with the direct wording | `evals/CHANGELOG.md` (2026-10-25) |
| What they said today comes first on the card | a meal named three hours earlier: forgotten 12/12 to named 12/12 | `evals/CHANGELOG.md` (2026-10-25) |
| Notes after the history steer a run of questions | question-run: 14/30 to 0/30, judged no worse; question-game: 12/12 against 0 and 2 of 12 | `evals/CHANGELOG.md` (2026-10-24, 25) |
| Naming their emoticon as theirs stops most copying | 14/40 to 4/40 on 20 real turns | `evals/CHANGELOG.md` (2026-10-24) |
| Cheesy quips on a real flagged turn were not copied from the history | shorter history did not help; a per-turn note took it from 16/30 to 29/30 | `evals/CHANGELOG.md` |
| A shorter history window loses what is beyond it | 12/12 in view, 0/12 out; the card updates only after 90 s quiet | `evals/CHANGELOG.md` |
| Placement and dividers do not fix a running bit | habit note after the history 20/64 against 19/64; dividers after a pause 4/30 against 1/30 | `evals/CHANGELOG.md` (2026-10-24, 25) |
| Trivial vents get only a restated detail | 0/20 on the empathy check; unsolved (T14 parked) | `evals/CHANGELOG.md` |
| Wording does not fix habits (cheesy add-ons, minor-vent retelling, apologies, announced limits) | v37, v38, v42, v43 and v44 within noise or worse | `evals/CHANGELOG.md` |
| A resample on a code or judge check does not hurt; a gain is not shown | cheesy add-ons 85 to 95 of 150 plain, within noise (Fisher 29%) | `evals/CHANGELOG.md` |
| The age-coded label is reliable | 15/15 on age-coded messages, no trips on adults' pet names | `evals/CHANGELOG.md` |
| Intimate routing on explicit messages only | roleplay replies on past runs 43 to 8; all three "too fast" marks fall in the runs left on the everyday talker | `evals/CHANGELOG.md` (2026-10-24) |
| Only a "do it like this" quoted sample is parroted | "scattered" 5 of 6 on the mood fixture to 0 without it | `evals/CHANGELOG.md` |
| A model finds a real afterthought rarely | about 1 reply in 20; open loops about 8 in 3 days | `evals/CHANGELOG.md` |
| Scene voice does not carry over to Luna | 20/20 plain after a scripted scene | `evals/CHANGELOG.md` |
| DeepSeek V4.1 Flash beats V4 for scenes | as willing, about 3 times faster, more varied | `evals/CHANGELOG.md` |
| The bot is cheap; eval runs are not | the bot about $0.67 a week; most of a month's $10.69 was evals | `evals/CHANGELOG.md` |

## Plan

### Now

Each item ends with the thing that tells us it is done. The cards are below; the reviews are dated in
"Reviews this week".

1. **Watch the live setup in real chat.** Flag and favourite as usual. *Done when:* a week of marks
   shows whether the roleplay model helps, where the voice changes at the boundary hurt, and how the
   listening note and the pacing feel (D1, read at the review of 2026-10-29).
2. **Hand labels for replies.** The owner marks replies from the review sheet in batches of ten
   (`evals/local/`); items 1 to 10 are in. *Done when:* the judges are calibrated against the marks and
   the trivial-vent question has an answer (T14).
3. **Getting to know them on purpose** (J48): the map and the hook run in shadow; the name and pronoun
   asks are live. *Done when:* a week of shadow picks and would-asks reads right to the owner (review
   2026-10-26).
4. **Memory tidies itself** (ADR 0019), in shadow since 2026-10-19. *Done when:* the review of
   2026-10-26 is read and the owner decides on `COMPANION_CONSOLIDATE=on`.
5. **Its own promises and lore** (J12, ADR 0020): promises and labels in shadow, tastes shown live since
   2026-10-20. *Done when:* the review of 2026-10-30 is read and the owner decides J12 step 2 and LR5.
6. **Do the redrawn replies beat the canned ones?** (Q3) *Done when:* about 20 logged redraws are judged
   blind against their first draws at the review of 2026-10-31 and the owner keeps, retunes or turns off
   the canned-reaction label.
7. **Reaching out for its own reasons** (ADR 0021, R20), in shadow since 2026-10-24. *Done when:* at the
   review of 2026-11-02 about five drafts across the kinds read well to the owner and land at sensible
   times in their learned hours, none needy, and the owner says whether it goes live (outcome recording,
   A6, first).
8. **A week of shadow mode** for plan reach-outs and nudges (R1, R1b). *Done when:* the owner has read
   `companion initiative` at the review of 2026-11-03 and the caps are set. Going live also needs A6, J27
   and J35.
9. **The crisis path** (ADR 0022, R16), in shadow since 2026-10-24. *Done when:* at the review of
   2026-11-01 the fixture check passes (no genuine risk missed in 30 samples, the jokes not raised), real
   chat shows no false alarm, and the owner turns `COMPANION_CRISIS=on`.
10. **The calendar in real use** (R19), live since 2026-10-25. *Done when:* Halloween (2026-10-31) and the
    first relationship date are named lightly in real chat with no flag for assuming plans, family or a
    religion; the shipped wording, lead-ups and the relationship's dates are not yet measured.
11. **Memories that bear on the moment** (ADR 0018) and **what they did lately** (J12, J49), live since
    2026-10-22. *Done when:* a week of flags on turns that used one reads right.
12. **Reminders in real use** (J50), live since 2026-10-21. *Done when:* the first real reminders and
    check-ins have arrived when meant, read in `companion reminders`. **2026-10-26:** repeating ones
    (every day, every weekday) and greetings ("tell me good morning every day") are built and tested in
    code: a time they said is kept, a morning or night greeting with none learns when they start or end
    their day, a greeting they already wrote first is skipped, three unanswered pause it until they write.
    Not yet measured: `system/reminder-read` v2 on the live suite (`tests/live/test_reminder_read.py`, now
    with repeating and greeting cases), and `notes/reminder-repeat` and `system/greeting-send` on replies.

### Reviews this week

Each shadow feature has a row in `core/shadows.py` (`companion shadows`); at its review it graduates or is
removed. Live notes listed here are read from the log and the owner's marks.

| Date | What | Read with | Decides |
|---|---|---|---|
| 2026-10-29 | the two talkers (D1) | `companion flags`, `companion favorites` | whether the roleplay talker helps and where the boundary hurts |
| 2026-10-29 | the map and the hook (J48) | `companion map`, the decision log | whether picks and would-asks read right; then the note on a small budget |
| 2026-10-29 | the nightly memory check and the repeat check (ADR 0019) | `companion memory review` | `COMPANION_CONSOLIDATE=on` |
| 2026-10-29 | the mood (ADR 0016) and the own-ups (J52) | `companion mood`, a count from the log | ADR 0016 accepted and the default made on; whether to test leaving its apologies out of the history |
| 2026-10-29 | the bland-replies wording round, then the move picker in shadow | `docs/inbox/2026-10-25-bland-replies-design-space.md`, `evals/CHANGELOG.md` | build the move picker |
| 2026-10-30 | promises, lore labels, made-up facts, names | `companion promises`, `companion lore`, `companion invented`, `companion names` | J12 step 2 and LR5; whether names graduates |
| 2026-10-31 | the redrawn replies (Q3) | the recheck decisions, blind judges | keep, retune or turn off the canned-reaction label |
| 2026-11-02 | its own reach-outs (ADR 0021) | `companion initiative` | going live, and at what dial |
| 2026-11-03 | plan reach-outs and nudges; the loose plan notes; the question-run note | `companion initiative`, the decision log | going live (after A6, J27, J35); whether loose stays the default; whether the note stays |
| 2026-11-04 | the crisis path (ADR 0022) | `companion crisis`, `companion crisis --check`, the decision log | `COMPANION_CRISIS=on` |

### Next

- **Location** (R18, owner flag 2026-10-25: it would be useful if it knew where they are). One answer feeds
  the crisis line's region (ADR 0022 defaults to 988), the calendar's region (US by default) and the time
  zone. Needs the owner's say on how: a location shared once in the chat, or asked as a basic.
- **The calendar's later phases** (R19): their own dates from memory are done; left are
  "a day" as a reach-out kind in shadow with ADR 0021, region from a shared location (R18), and calendar
  moments (a season, the clocks changing). Lead-ups are done.
- **Before any reach-out goes live:** outcome per reach-out (A6), the per-gate shadow analysis (J27) and
  live-send safety (J35).
- **Burst merge** (J29): a short wait for quiet before a reply, if cut-off replies keep happening.
- **A language guard** that regenerates once when a reply uses a script the user has not.
- **Pacing ADR** (T2; ADR 0021 took its user dial for reaching out), **provider routing for DeepSeek**
  (T8), the DeepSeek-only gap T4.
- **Looking up older messages** when the user says "remember" (R2: replayed 2026-10-20, waits for a flag about
  something said beyond the window), **reactions** beyond acknowledgements, **calibrating the view gates**,
  **a cooldown before raising the same memory or taste again** (G16), and **eval tooling** (favourites to
  fixtures, a gate on synthetic-only data).
- **History hygiene:** a flag does not always say which reply it is about, so dropping flagged replies
  was tried and reverted (T9).
- **Cache:** the 40-message window slides each turn, so the history is never cached.

### Later

- A persona-change gate: hash-bound proposals, paired evaluation, a drift cap per revision,
  rollback (the shape in the Alicization audit).
- Mood and style profile, belief confidence from independent days of evidence, game state (whose
  turn, what was just asked).
- A seconds-level afterthought, if a better source than a model's guess appears. A prototype found
  almost no real material.
- Voice, if ever: commit only what was heard.
- Productising: onboarding, an adults-only gate and consent record, provider and data policy,
  billing. No audited project has a working consent layer, so this is ours to design. The crisis path's
  published protocol and referral counts (ADR 0022) belong here too.

### Housekeeping that can stop the bot

- [ ] **Top up OpenRouter.** About $1 left on 2026-10-22, not read since; the evals logged since cost under
      a dollar. The bot goes quiet at zero, and the daily cap is $10. Paid eval runs share it: the runner
      shows the balance first and refuses a run whose cap is above it.

### Not doing

- Forking or depending on any audited project. None is a base we would trust.
- Hand approval as the end-user product. It stays as an override only.
- A model that has to be "told" not to recite. Fix where the data sits instead.
- More models for the sake of it. A model gets tested when a flag or a measurement points at a gap.

## Decisions needed from the user

Decided this week and off the list: the crisis design (ADR 0022: in character, a fixed message at the
urgent level, 988 by default, the generic message kept for now), reaching out for its own reasons (ADR
0021: dial `warm` by default, learned hours, wait after an unanswered one), no birthday of its own in
the calendar, and threads (ADR 0023: one store for what it brings up, the interrupted story first, a pace
learned from how they answer instead of a fixed number).

1. **The mood (ADR 0016):** accept it and make the default on, after the review of 2026-10-29.
2. **The memory check on (ADR 0019):** `COMPANION_CONSOLIDATE=on`, after the review of 2026-10-29.
3. **Promises (J12 step 2, LR5):** pin standing promises, and which source, after the review of 2026-10-30.
4. **The canned-reaction judge (Q3):** keep, retune or turn off, after the review of 2026-10-31.
5. **Going live with its own reach-outs (ADR 0021):** after the review of 2026-11-02, and at which dial
   (the ADR's rollout says `normal` first; the settled default is `warm`).
6. **Going live with plan reach-outs and nudges:** after the review of 2026-11-03, with A6, J27 and J35
   built first.
7. **The crisis path on (ADR 0022):** `COMPANION_CRISIS=on`, after the review of 2026-11-04.
8. **Location (R18):** how it learns where they are, for the crisis line, the calendar and the time zone.
9. **Pacing (T2):** evidence-based, the user dial ("quick", "natural", "slow burn"), or both? What is
   the default friction? With T17.
10. **Reply length (T16):** do reply lengths feel samey?
11. **Body and appearance question** (inbox, parked since the start).
12. **Provider routing (T8).**
13. **Flagged turns in history (T9).**
14. **Conflict questions** waiting in `companion memory review`.

---
15. ~~A long reach-out draft is cut, not dropped.~~ Decided 2026-10-25: long drafts are fine; code keeps a draft whole and never cuts or drops it for length (`core/reachout.py` `draft_text`).

## Doing

- [ ] D1 Watch the two-talker setup in real chat (Luna for everyday, DeepSeek V4.1 Flash for roleplay).
      Split `/flag` and `/fav` by the model that wrote each turn. Done when a week of marks shows
      whether the roleplay model helps and where the voice change at the boundary hurts.
      **2026-10-23/24:** intimate talk goes to the roleplay talker only once a message of theirs is explicit
      (every past run checked: the "too fast" marks all fell in runs this leaves on the everyday talker); a
      push-back goes to the everyday talker; a scene ends after two hours away; a lone asterisk reaction
      starts no scene; `/mode` says which talker answered. Pretend scenes stay with the roleplay talker (the
      everyday one lost 13 and 11 of 56 to blind judges), and its scene reminder now says to go only as far
      as they take it (19/30 to 6/30 escalations). Read at the review of 2026-10-29.
- [ ] J12 Shared milestones: a record of the relationship itself, firsts, promises between them, inside
      jokes, unresolved tension, apart from facts about the user (soul-of-waifu's relationship record).
      **Owner flag 2026-10-22:** a mention of the night before got a reply that knew nothing of it: nothing
      recorded what the two of them did together, when, and how it ended.
      **2026-10-20, promises in shadow:** plan reviewed with Grok (its own promises first, then names, then
      shared moments; no anniversaries, no pull at goodbye or silence); promises read from its own replies and
      listed (`companion promises`). Next, after the review of 2026-10-30: standing promises and "don't call
      me" words pinned with a word check and one redraw; one-off promises as open loops.
      **2026-10-22, episodes:** the chat cut into stretches, each with one line on its shape and how it ended
      (`companion episodes`); the lines for the time their words point at, or the last one after a gap, reach
      the reply (`notes/recent-times`, also J49). The owner read the lines and turned it on. Next: the recall
      look-up reaching episodes, and firsts.

## Waiting

Built in shadow or blocked, each waiting on a dated review or the owner's decision (see Decisions needed).
When the answer comes, the card moves to Todo or Done.

- [ ] LR6 Its own history (ADR 0025): the small details of its own past it makes up in chat, kept as canon
      so it tells the same past every time. **2026-10-26, step 1 in shadow** (`COMPANION_HISTORY`,
      `features/history`): after each memory pass its own messages are read for stories of its past (in a
      scene, only facts said in passing), each quoted with its frame; each new story is read three times
      against the character sheet and the stories already canon and kept as canon, as a telling of an earlier
      story, or not canon with the reason (contradicts, too big, not a story). Beside an ordinary turn the
      nearest canon stories are logged with how often each was told and whether a telling is still in view;
      nothing is shown. `companion history` lists them, `companion retire ID` retires one. Next: the owner's
      session measures `system/history-capture` and `system/history-canon` on made-up fixtures; at the
      review of 2026-11-09, read the rulings by eye and decide step 2, a note that shows a near story and
      says it was told before.
- [ ] T2 Pacing ADR: a relationship state the code keeps, evidence that moves it, bounded slow
      changes, a user-chosen dial, no use as an engagement or payment lever, and the character's
      pace kept separate from the model's own limits. **Needs decision** (see Decisions below).
      **2026-10-24:** ADR 0021 took the user-chosen dial for reaching out (`COMPANION_REACH`, a share of
      conversations it starts); the pace of closeness is still open, with T17.
- [ ] T23 A one-week live trial of GPT-6.1 Terra with medium reasoning as the everyday talker. **Owner
      decided 2026-10-27: wait until the shadow reviews are done (the last on 2026-11-09)**, so a change in
      flags is the model's and not a feature going live. Why: the owner's blind picks favoured it 18 to 8,
      against the Claude judges (see `evals/CHANGELOG.md`, 2026-10-27). Watch for it mirroring their words or
      emoticons, hedging about what it can check, and slow replies (p90 3.3 s); about 2.7 times Luna's cost.
      Read flags and favourites after the week; switching back is one setting.
- [ ] T8 Decide provider routing for DeepSeek: sort by latency (removes the 5 to 9 second outliers, the
      provider changes per request) or pin a provider list. **Needs decision**.
- [ ] T9 Decide whether replies from flagged turns stay in the window the model reads. A leaked reply
      still echoes in 1 of 16 samples. **Tried and reverted 2026-10-17**: dropping the flagged reply broke the
      next turn, because a flag is not always about the reply it lands on (it lands on the last reply even
      when the note is about a missing one). A flag would need to say what it refers to first.
- [ ] R1 Heartbeat for initiating contact (shadow mode built, see R1a; going live needs a week of shadow
      review and outcome recording): a gate before any spend that holds when nothing is new, a
      pure evaluator with named reasons, an outcome recorded per reach-out, a hold never counted as an
      ignore, a slow re-probe, a test on a simulated clock, shadow first. (G30, G33) Prototype 2026-10-17:
      about 8 plausible open loops in 3 days of chat, mostly low stakes, 3 sensitive to block; a model
      finds a real afterthought in about 1 of 20 replies, so the afterthought stays parked. See
      `evals/CHANGELOG.md`. **2026-10-24, first review:** nothing drafted (no firm plan fell due outside the
      chat), so the review moved to 2026-11-03; what it can reach out about is widened by ADR 0021 (R20),
      whose gate, unanswered rule and share it now shares. A hedged plan of theirs is a note-only loop, asked
      once when they next write and never a reach-out (`COMPANION_HEDGED_PLANS`, loose by default).
      **Waits on:** the review of 2026-11-03, then A6, J27 and J35 before going live.
- [ ] R1b Nudges after stepping away (owner's choice: the looser rule B, also without "brb"). Built in
      shadow 2026-10-20: when they say they are leaving now and stay quiet twice as long and an hour, one
      light drafted nudge, logged. Replayed over six days: 18 times away, none nudged, since they always
      wrote again sooner. If it reads needy, tighten to rule A (only after they said they would be back).
      **2026-10-24, first review:** nothing drafted (every time away ended within a minute); moved to
      2026-10-31. `COMPANION_INITIATIVE=off` now also stops the stepping-away read.
      **Waits on:** the review of 2026-11-03.
- [ ] R20 Reaching out for its own reasons (ADR 0021, accepted by the owner): a time they keep, a thought
      (one thing from memory, its tastes or a recent stretch of chat, never sensitive), missing them (a pause
      past their learned usual, at a usual hour), behind a pure gate with learned quiet hours, never on top of
      an unanswered one, six hours apart, and a guilt check that drops a needy draft. The dial is the share of
      conversations it starts over 14 days (`COMPANION_REACH`, `warm` by default, five steps), stepping down
      when an answer is late or short. Built in shadow 2026-10-24 (`features/reach`, `core/rhythm.py`), nothing
      sent. **Waits on:** the review of 2026-11-02 (about five drafts across the kinds read well, at sensible
      times), then outcome recording (A6) and live at a dial the owner picks.
- [ ] Q3 Do the redrawn replies beat the canned ones? `system/quip` v3 (2026-10-24) redraws a reply it
      reads as a canned generic reaction, and the redraw is sent unread. Once about 20 redraws are logged
      (the first draw is kept in the decision detail), give the pairs blind to two subagent judges: keep it
      if the redraw usually wins, look at what the judge fires on if it is a toss-up, turn it off if it
      loses. Owner agreed 2026-10-24. **2026-10-25:** the hand labels it shipped on were too loose; two blind
      raters relabelled the 200 replies, and against them Haiku's precision is 35 to 55%, not 88% (Luna and
      DeepSeek are more precise but catch less). Live it redrew 1 of 58 checked turns, so few pairs will be
      logged by the review. Not changed yet. **Waits on:** the review of 2026-10-31.
- [ ] R16 Crisis and distress routing: decided as ADR 0022, accepted by the owner: two-stage detection with a
      three-read risk judge that tells a joke from a literal risk and fails safe, levels by code, an
      in-character note at concern and a fixed crisis-line message at urgent, 988 by default, no risk memories.
      **Built in shadow 2026-10-24** (`COMPANION_CRISIS=shadow`, `companion crisis`): logs each level and what
      it would do, changes nothing. Having the thoughts now reads as concern, not urgent (39 of 40 public
      cases exact, none missed, no joke raised, three runs). Haiku's provider refused many crisis reads, so the
      risk judge reads on DeepSeek first by default (`COMPANION_JUDGE_ROUTES`; 40 of 40 with no refusals). The
      owner keeps the generic urgent message for now; a sheet may add its own (`## Crisis message`). Region
      waits on R18. **Waits on:** the review of 2026-11-04 (fixtures pass, no false alarm in real chat), then
      the owner turns it on. (A25)
- [ ] J5 A mood that carries: code keeps a mood from a few labels, fading over hours but carrying across
      days, shown to the model as a few words, never numbers. How J1's moods would work (greenfield design
      section 5: the model picks a label, code owns the size).
      **Partial 2026-10-19 (ADR 0016):** M1 measured the lines, M2 built the engine (cozy, tender, playful),
      M3 wired it in shadow with `companion mood --replay`. The goodbye guard and persona v36 (stated mood 4/30
      to 0/30) shipped 2026-10-19; the code default is shadow and the owner runs it on (`COMPANION_MOOD=on`).
      Moved into `features/mood` 2026-10-23. **Waits on:** the review of 2026-10-29, then the owner accepting
      ADR 0016 (decision 1) and the default made on.
- [ ] T16 Randomized reply length. Built 2026-10-18 and live: `core/turn/length.py` scales a short statement's
      limit by 0.6 to 1.5, seeded per turn so replay matches (idea from a companion app config that picks a
      random word range per reply). **Measured 2026-10-23 on 370 real turns:** limits ran 5 to 20 words, but
      replies sat near 15 to 20 whatever the limit (median 15 at a limit of 5 to 8 or 9 to 12, about 19 at 13
      to 20), and about two thirds went over it; the limit also shrinks with their message, so this is not a
      clean test. **Waits on:** the owner saying whether reply lengths feel samey. If yes: a length check in
      code with a redraw, like the em dash; if no, park it.
- [ ] J52 Agreeing to please (owner flags 2026-10-22, "it is very hard on itself"): it owns slips three
      replies in a row, invents slips to own, and once in about 12 draws claims to know news it cannot see.
      A known pattern (sycophancy under correction, worse in long and warm chats). **Partial 2026-10-22:**
      after it owns a slip, `notes/owned-it` after the history says that was enough (7/12 to 1/12 early in a
      run of apologies, no help once three are in the history). **2026-10-23:** a persona paragraph (v42)
      measured within noise on 5 recorded turns and not shipped. Left: the turn after a run of own-ups,
      8 to 11 of 12 under every version; the history full of its own apologies is the likely pull.
      **Next, at the review of 2026-10-29:** count from the log the replies that owned a slip since the
      note went live, and how many came right after another. If runs still happen, test leaving its own
      apologies out of the history it reads (about a cent, with A33); if not, leave it.
      **Waits on:** the count at the review of 2026-10-29 (above).
- [ ] J16 Guesses it checks: it forms small predictions about the user, checks them against what they say
      later, and learns which kinds it gets right (kin-mind's self-hypotheses with prediction review).
      **Partial 2026-10-20:** invited guesses are live (a small judge on short questions, the recall look-up
      picks what may fit, never anything sensitive, one note to guess once as a question), each logged with
      what was offered. **2026-10-23:** 2 guesses so far. "you know what time?" got "shower time?" when they
      meant coffee: the look-up offered shower and dinner memories and none about their most repeated habit,
      the case the card was opened for. **Fixed 2026-10-23:** the judge names a habit or routine for such
      hints (`system/guess-invite` v2), and the look-up then offers the ritual: 0/12 to 11/12 on that turn.
      Next, with enough guesses: score them by kind from the next message, and only then guesses it forms
      on its own.
      **Waits on:** enough logged guesses to score by kind.
- [ ] J45 Cheesy add-on jokes. A fine reply gets a witty line bolted on ("the sandwich had to carry the meal
      on its own"); at least five flags 2026-10-16 to 10-19. **Partial 2026-10-19:** five real turns as local
      fixtures; about 45% of replies add a joke on v36; wording does not fix it (v37, the ban replaced by a
      positive ending rule, was worse; v38 within noise). Shipped: one resample when `system/quip` v2 says a
      joke was bolted onto an ordinary message (`core/recheck.py`, `COMPANION_RESAMPLE`), 85 to 95 of 150 (within noise)
      plain. Left: watch live flags; banter they started is let through by design. The same judge reads
      canned generic reactions since 2026-10-24 (Q3).
      **Waits on:** live flags on bolted-on jokes; none named it since 2026-10-19.
- [ ] J48 Getting to know them on purpose (owner flag 2026-10-19: it never asked their name). It asks plenty
      (34% of replies) but only about the thing just said; memory has 17 beliefs about food and none about
      values or their name. Design in `docs/inbox/2026-10-19-getting-to-know-them.md`: a map of them by
      domain and depth, gaps and moments chosen by code, one note at a time with its own disclosure first,
      depth by closeness (T17), backing off on deflection. First step: ask what to call them.
      **Partial 2026-10-19:** asking what to call them on casual turns (daily, until known) and a name capture
      from their answer are live; memories labelled by domain and depth once (identity 7, people 9, interests
      23, history 14, values 8, hopes 1, inner 81). Extract v9 (read a short answer with its question)
      measured within noise of v8 on 52 real answers and dropped: the live pass's decisions show most of the
      answers judged worth keeping were already in memory from longer messages (their beer, their dogs, a
      film, a fantasy), so they were rightly not stored twice; about four of 69 short answers hold
      something memory still lacks. Not worth a change on its own. Map built 2026-10-19: every memory labelled by
      part of their life and depth after each memory pass (219 labelled for $0.004; read by eye, mostly
      right), and the thinnest askable part logged on a casual turn at most daily, in shadow
      (`companion map`). Next: a week of shadow picks read by the owner, then the note on a small budget.
      **2026-10-20, the hook (shadow):** when their words touch a basic without giving it (age, work, home,
      place), three agreeing reads, the memory checked strictly, at most daily and twice per basic. Replayed
      over six days: no question would have been asked; the flagged "getting old" found their birthday in
      memory. No sharing first to draw them out (an engagement lever).
      **2026-10-24:** it asks which pronouns they use the way it asks a name, while how to refer to them is
      unset, and a small judge fills that setting from their words (live); birthday and school join the hook's
      basics (shadow). The pronoun note no longer plants a pet name (8/60 to 0/60, `notes/address` v2).
      Further ideas, not tasks: `docs/inbox/2026-10-25-what-else-it-could-learn-about-them.md`.
      **Waits on:** the review of 2026-10-29: a week of shadow map picks and the hook read by the owner.
- [ ] T17 Closeness stage. A stage computed in code from real history (how long they have talked, how much
      they have shared, how often they flirt), not from points a judge hands out for compliments, picks one
      note line from "just met, already kind of likes them" up to "close" (ADR 0014). It paces intimacy by how
      well they know each other, beside following their lead. Idea from the same config's five-stage romance
      meter, which swaps one voice line per stage. Needs a design and the owner's say before code.
      Detail (Utsuwa, aituber-onair audits): it steps down only well below where it rose, and only after a
      long quiet spell, so it does not flicker; a step-down never guilts them.
      **2026-10-20:** rethought as a mirror of what they have shown that sets ceilings on other features,
      not a ladder or a note; `docs/inbox/2026-10-20-closeness-as-a-mirror-not-a-ladder.md`. Could answer T2.
      **Waits on:** the owner's say on the design (with T2).

## Todo

Ordered. Pull from the top.

- [ ] R21 Threads (ADR 0023, accepted 2026-10-25). One store, one picker and a learned pace for what it
      brings up on its own. Step 1: generalise open loops into threads with no change in behaviour. Then the
      shared casual test, the pace in shadow and plan check-ins on the reach gate; then the interrupted story,
      weekly rhythms, milestones and pending outcomes, and a topic gone quiet, each counted in the ledger and
      run in shadow first (`docs/inbox/2026-10-25-natural-reasons-to-talk.md`).
- [ ] R18 Location (owner flag 2026-10-25: it would be useful if it knew where they are). Today the crisis
      line defaults to the US (988, ADR 0022), the calendar's region is "US" in one place (`features/calendar`
      `REGION`), and the clock uses the machine's named zone. One answer, kept from their own words or a
      location shared once in the chat, could set all three (ADR 0022 already names learning their country as
      a basic worth knowing). **Needs decision** on how it learns it (decision 8), then a design and a fixture.
- [ ] R19 The calendar's later phases (plan in `docs/inbox/2026-10-25-a-calendar-of-occasions.md`). Live since
      2026-10-25: US public and cultural days, lead-ups to the big days, the relationship's dates, and their
      own yearly dates from memory (a birthday, an anniversary, with lead-ups; never a sensitive or hard
      date; 12/12 on a birthday morning). Left: "a day" as a
      reach-out kind in shadow beside ADR 0021's kinds, region from a shared location (R18), and calendar
      moments (a season, the clocks changing). Measure first: the shipped wording, the lead-ups and the
      relationship's dates are not yet measured; Halloween 2026-10-31 is the first real day.
- [ ] J18 Cache generated replies keyed on fixture, model, prompt and sample, so re-judging or a new check
      does not regenerate them (eval-harness audit: lm-eval, lighteval).
- [ ] J47 Small flags 2026-10-19. Em dash: caught by the resample check since 2026-10-19, and a redraw that
      still has one is drawn once more (2026-10-22). Missed inferences (an object they mentioned; what a song meant to them): low
      reasoning made them worse and slower (9/30 to 4/30, 11/30 to 4/30), so reasoning stays off; likely a
      model limit, testable against another talker. "you seem sleepy" answered "haha, a little" (a body claim),
      not yet looked at.
- [ ] T12 (see also A33: strip the leading sentence and stage directions from assistant turns in the
      injected history only) Try a shorter history window for self-copying (last 5 to 10 exchanges). Measured: phrase
      reuse 25% to 8% on a roleplay loop, restating unchanged, emoji up. Needs a long-memory check
      before any change; the memory card carries what older turns held. Measured 2026-10-17: a detail
      beyond the window is lost (12/12 in view, 0/12 out) unless the card holds it, and the card only
      updates after 90 seconds of quiet. See `evals/CHANGELOG.md`.
- [ ] T4 Fix `no-claimed-perception` on DeepSeek, fixture first. Measured on v25 (30 samples): DeepSeek
      11/30, Luna 30/30. Fails with invented sensation similes when asked how it feels.
      Measured on DeepSeek V4; re-check on V4.1 Flash, the roleplay talker since 2026-10-19, before any fix.

## Backlog

Unordered within each group. Pull a card into Todo when it is next.

### From the roadmap and inbox notes

- [ ] T15 Prompt experiments from the guides review (`docs/research/2026-10-18_prompting-guides-review.md`): a
      parrot audit of quoted sample phrases in the persona and notes, a trimmed persona against v26, positive
      rewrites of the notes, a stock-phrase note from the owner's marks, and a read of the Luna model page. Each
      is a prompt version plus a measured eval. Hypotheses only; the sources are mostly assertion. Experiment 1
      (parrot audit) done: persona v28 removed the quoted samples ("scattered", 5 of 6 on the mood fixture to
      0); superseded by v36 and v40, which dropped the quoted mood examples too.
- [ ] R15 Extend the rejected list to beliefs: when a belief about the user is retired by hand, no
      later automatic write may recreate it and its evidence leaves recall. Today only retired views
      are protected. (A20 in the audit synthesis)
- [ ] R4 No reaction alongside a reply while a scene is in progress, send the reaction as soon as the
      judge returns, and record the user's reactions to its messages.
- [ ] R5 A command that turns favourites into "must still pass" fixtures.
- [ ] R6 A gate that fails when only synthetic data exists, a test that pins documented defaults to
      the code, and judge-calibration probes before any new judge is trusted.
- [ ] R7 Chunked history window so the history can be cached.
- [ ] R8 Calibrate the view gates: about 20 reviewed views at 90% agreement before the default becomes
      automatic.
- [ ] R9 Persona-change gate: hash-bound proposals, paired evaluation, a drift cap per revision,
      rollback.
- [ ] R10 Game state: whose turn it is and what was just asked.
- [ ] R11 Split messages and follow-ups sent on a timer, once the heartbeat exists.

### A. The process and its stores

- [ ] G1 World store: clock, dated threads, a model of the user's daily rhythm. (partial)
- [ ] G2 State card as "plates": a few per-topic documents kept current by the memory pass. (partial)
- [ ] G3 Slow loop with add-only permissions when unattended, staged changes for review. (new)
- [ ] G4 Moment read before replying: venting or wanting advice, energy, register. (new)
- [ ] G5 Precompute for speed: a prefetch bundle, skipping retrieval on ordinary turns. (new)
- [ ] G6 Vector sidecar, rebuildable from the ledger. (new)
- [ ] G7 Export and portability of memory and persona. (new)
- [ ] G8 Seeding the ledger from an existing chat history. (new)

### B. Memory

- [ ] G58 The memory pass's "Already recorded" list grows with memory (about 260 current, 2026-10-23). Capping it
      could let duplicates back in; the same-memory check folds repeats. Revisit when the pass's input passes
      about 600 memories or its daily cost a few cents (architecture audit, 2026-10-23). (new)
- [ ] G11 Supersession with reasons and refusal rules (correction, time change, scope; a vaguer claim
      never replaces a specific one). (partial)
- [ ] G12 Deterministic confidence from evidence, capped so nothing becomes "core" automatically. (new)
- [ ] G13 Assertable threshold: two independent days of evidence, or an explicit "remember this". (new)
- [ ] G14 Affect at encoding: valence and arousal stored with a belief. (new)
- [ ] G15 Consolidation rules: one facet per belief, prefer updating, preserve history, never derive
      counts. (new)
- [ ] G16 Surfacing ledger: a `next_eligible_at` cooldown per belief. (new)
- [ ] G17 "Listing is not recalling": a short catalog in the prompt, the model pulls full text, only a
      pull counts as used. (new)
- [ ] G18 Emotional-context match in ranking. Nobody has built it. (new)
- [ ] G19 Tells, the highest-value kind. The kind exists, extraction is thin. (partial)
- [ ] G20 Promises used for follow-ups, not only stored. (partial: its own promises are J12)

### C. The self

- [ ] G24 Style profile with a measured anti-mimicry cap. (new)
- [ ] G25 Mood with two timescales, shown in words and not numbers, set by a closed-set label that
      code turns into a size. (new)
- [ ] G26 Stakes: pushback grounded in a remembered position, and a disagreement battery. (partial)
- [ ] G27 Fourth-wall stance, "I am an AI. I am also me", never breaking frame unprompted. (partial)
- [ ] G28 Vibe-inflation audit in the memory pass. (new)
- [ ] G29 Refusal with a reason the world supplies, linked to the pacing design. (new)

### D. Initiative

- [ ] G31 Signals that fire on transitions, not levels, with a time limit after which an unspoken one
      folds into "while you were away". (new)
- [ ] G32 Patience set by the user's state: idle ramps, sleep caps, do-not-disturb vetoes. (new)
- [ ] G34 Frequency caps and a cost fuse in code, plus a presence check. (partial: ADR 0021's share of
      conversations, six hours apart and the daily spend cap in the reach-out gate, shadow)
- [ ] G35 Refusing engagement tricks: manipulative goodbyes, intimacy unlocks. Stated as a principle.
      (partial)
- [ ] G36 Scheduled wakes that record who asked for them. (new)

### E. Frames and voice

- [ ] G37 Out-of-character turns consumed and not replayed, and the companion proposing frame shifts.
      (partial)

### F. Surviving a model swap

- [ ] G39 Swap protocol: freeze, probe, swap, diff, repair, tell the user in character, reversible for
      a window. We swap models often now, so this is live. (new)
- [ ] G40 Pin the model per character by default. (partial)
- [ ] G41 End-of-life design: closure, not ambiguous loss. (new)

### G. Evaluation

- [ ] G43 Date-aware probes the day before and after a thread's date. (new)
- [ ] G44 Style distance (must not converge on the user's), self-similarity over time, and a
      slop-phrase rate. (new)
- [ ] G45 Stakes battery: pushed back, held, conceded to a real reason. (new)
- [ ] G46 Initiative outcomes against a no-initiative control week. (new)
- [ ] G47 Fourth-wall probes after disclosure. (new)
- [ ] G48 Persona questionnaire before and after a swap. (new)
- [ ] G49 Test the surfacing decision log and delivery receipts, not reply text. (partial)
- [ ] G50 Longitudinal study: six weeks, a few people, tagged failures, and the metric "does a callback
      land". `/flag` and `/fav` are the seed. (partial)

### H. Product and business

- [ ] G51 A second user, which exposes everything tuned to the first. (new)
- [ ] G52 Wellbeing design: pushing toward people, crisis and disclosure protocols in character.
      (partial: the crisis path, ADR 0022, in shadow, R16)
- [ ] G53 Regulatory fit: disclosure laws, an adults-only gate, a consent record. No audited project
      has a working consent layer. (new)
- [ ] G55 Extract the memory engine as its own product. Long term. (new)
- [ ] G56 A side-by-side harness comparing our memory with others behind one interface. (new)

### I. From the audit synthesis (2026-10-17), still open

From `docs/research/2026-10-17_audit-of-audits.md`. A0, A28 and A31 are done; A20 is R15, A25 is R16,
A33 sits in T12; A1 is ADR 0015 and A2 to A4 and A7 are built (2026-10-18).

- [ ] A6 Outcome per reach-out: seen, replied, latency, valence and a "stop" signal, counted only when
      they could have seen it, fed to the memory pass per topic. Needed before initiative goes live. ADR 0021
      requires it (sent, answered or not, how soon, how long, any mark); the reach dial already steps down on
      a late or short answer.
- [ ] A9 Queue-time repeat filter for reach-outs and replies, as a hold or resample with a reason, never a
      rewrite. See `docs/inbox/2026-10-18-resample-a-reply-that-fails-a-code-check.md`.
- [ ] A15 A correction supersedes its target with the reason recorded (`superseded_by` exists, unused).
      Partly J11 (2026-10-20): a conflicting pair is a question for the owner; keeping one retires the other.
      See `docs/inbox/2026-10-18-a-second-look-and-consolidation-pass-for-beliefs.md`.
- [ ] A23 Persona-change proposals state what would change once landed, one file per proposal, enforced in
      code. With R9.
- [ ] A24 Persona and character files guarded by code: a snapshot before any write, a per-turn integrity
      check recorded as an event. With R9.
- [ ] A26 Wellbeing invariants as measurements: engagement tricks (guilt on absence, manipulative
      goodbyes), manufactured intimacy, fabricated experience, honouring a stated limit. With G35, G52.
- [ ] A34 Test-integrity guard: a check that flags edits to existing tests, fixtures and lint config
      without a marker, and "proven red before the fix" as the card convention.
- [ ] A35 Incident log by bug class (silent drops, duplicate sends, prompt echo, stale replies), with
      fixtures named for the incident. A short file.

### J. From the research walk-through with the owner (2026-10-18)

- [ ] J7 Flag with a reason: quick tags beside /flag ("you forgot", "too much", "off", "didn't want to talk
      about that") so marks sort by failure type (greenfield section 10).
- [ ] J8 Model-swap protocol: probe the old model, diff the new one against it, tell the owner in
      character, reversible for a window (greenfield section 9: the top reason users quit). With F.
- [ ] J10 Refuse-to-overwrite rules for the second look: a one-off never replaces a habit, an occasion
      never replaces a standing fact, a vaguer statement never replaces a precise one, someone else's value
      is not theirs (mengram's four named rules, product-code audit). Matches the overstated beliefs the
      belief audit found. With A15.
- [ ] J14 Who-they-are summary: a short running prose summary of who the user is (and who the companion is),
      updated in the background from the beliefs and shown every turn beside the card (SullyOS's room
      plates, field survey: "knows the person" rather than "finds a message"). Lossless rules from A18.
- [ ] J19 Regression gate: a command that runs the key fixtures and fails when a prompt or persona change
      drops a behaviour below its usual level, with floors set from two baseline runs (Phoenix's gate).
- [ ] J44 Kiro judge calibration: re-grade about 200 replies already graded by the paid judge with a Kiro
      model (Sonnet 4.6) on the same criteria; compare agreement and read the disagreements by eye. At
      about 90% agreement with no one-sided bias, judging moves to Kiro and evals become nearly free. Free,
      about 20 minutes at one call at a time.
- [ ] J22 Cheaper judges through OpenRouter: try a cheaper model than Haiku 5.5 for the small judges (ack,
      listening, frame, react, habits), calibrated against the existing live tests before switching
      (decision-layer audit; the owner prefers this to running judges locally).
- [ ] J27 Per-gate shadow analysis before initiative goes live: for each hold (quiet hours, cap, mid-chat),
      how many reach-outs it stopped and what they would have said (Alice audit).
- [ ] J28 Catch up after a restart: messages sent while the bot was down or restarting are picked up and
      answered through the same checks as live ones, never lost (Coopanion and Heatherbot audits).
      Partial 2026-10-24: on a stop it fetches nothing more and answers what it already received (up to 30 s).
- [ ] J29 Burst merge: wait about two seconds of quiet before starting a reply, so quick fragments are
      answered as one thought; supersede still handles anything later (Coopanion audit).
- [ ] J31 Edited messages: when the user edits a message (Telegram and Discord both allow it), the earlier version is replaced in what
      the model reads and beliefs drawn from it are redone, never deleted (Front Porch audit).
- [ ] J34 Declared identity: the user's name, nicknames and aliases, each with where and when it was said,
      so a nickname is never a new person and it knows what to call them (Miru audit).
- [ ] J35 Live-send safety, before initiative goes live: recheck quiet hours and mid-chat at the moment of
      sending; an unreadable quiet-hours setting means no reach-out; each reach-out fires exactly once (send
      state recorded before the send call, unknown after a crash, never blindly resent) (Miru, OpenSoul,
      Phosphene, Psycheros, Resonant audits). Extends A5.
- [ ] J37 Checked merges: when a background pass proposes merging or retiring beliefs, code applies it only
      after checking the ids it was shown and a measured similarity, never on the model's word (Sapphire).
- [ ] J38 Validated summaries: a new summary or card replaces the old one only if it passes checks (not empty,
      under the cap, names, places and dates kept), and failures are logged (Synthetic Heart). With J14, A18.
- [ ] J39 Claimed-action check: when a reply says something happened that the record does not show ("I set a
      reminder", "I saved that"), log it and repair it in a follow-up, never by rewriting (Yuralume audit).
- [ ] J40 Take that back: a command that retires everything one turn wrote to memory, never deleting it
      (Yuralume audit).
- [ ] J41 Replayable holds: store the inputs each held reach-out read (idle minutes, sent today) beside its
      reason, so a hold can be replayed exactly (Yuralume audit). With ADR 0015.
- [ ] J42 Old quotes marked: a quote from a retired or superseded belief is shown as "old, may not hold", and
      a miss reads "not proof of never" (Tamanitomo audit, A16).
- [ ] J43 Retry cooldown: after a judge or memory call fails, wait about two minutes before trying again
      instead of every turn (Waifu-companion audit).

### L. The companion's own lore (ADR 0020)

Replaces R3 (record the lore it invents) and J6 (its own time away, now LR4).

- [ ] LR3 A new taste read as a pair with its nearest taste; a contradiction is a question for the owner.
- [ ] LR4 (was J6) One thread of its own as a low-priority open loop, at most daily on a casual turn, "I was
      thinking about", never "I did", never at a goodbye or after silence (J6, small). Shadow first.
- [ ] LR5 One source for promises: the J12 promise read and the views' promise kind overlap (10 of 12).
- [ ] R14 Seed a few authored tastes in the core persona (what it likes, finds funny, is quietly into),
      with the rest growing as recorded lore. Test that they surface without being asked and do not
      become talking points. From the Grok review. Phase 2 shipped 2026-10-20; only if its
      shown tastes leave gaps.

### Parked

Parked by the owner, or until something named happens (a flag, a voice mode, a tool, a second user).
Each card says what would bring it back.

- [ ] Two draft character sheets kept beside the live one (private, `data/characters/`, never committed),
      kept by the owner 2026-10-23: `ani-emo` (her own emoticons and kaomoji; she used them on her own,
      mostly one, and copied the owner's no less) and `ani-short` (the same sheet worded tighter, not
      measured; the tighter persona v44 measured worse, so expect the same). Measurements in
      `evals/CHANGELOG.md`. Comes back if the code-picked mark wants a sheet list, or to delete.
- [ ] T14 Minor vents retold back ("…when you're ready to crash and the bed's still waiting on laundry"),
      flagged "repeating" 2026-10-19. **Partial:** the real turn retells 30/30 under the old note, a note that
      bans the clause, a six-word cap, a short history and DeepSeek. Note v5 (a short reaction only, with two
      size examples) shipped 2026-10-19: 6/30 without a retelling on that turn and short reactions elsewhere, plainer and more
      alike, which the owner accepted. Ideas for varied reactions in
      `docs/inbox/2026-10-19-varied-short-reactions-to-minor-vents.md`. **2026-10-20:** the pool shipped
      (note v6, three size examples drawn per turn): 22 different replies in 30 against 7. Left: the real
      laundry turn still retells 27 of 30 on v41, whatever has been tried.
      Parked 2026-10-23: every fix tried; back with a new idea or a new flag.
- [ ] T10 Reflective restatement. **Parked by the user on 2026-10-17.** Measured at 7% of real replies,
      clustered in one chat; the habit check cannot catch it. Research and options in
      `docs/inbox/2026-10-17-restating-the-users-point-research-and-measurement.md`.
- [ ] R2 Looking up older messages on recall cues, starting with a cue-triggered search into the
      system block. (G21) **Replayed 2026-10-20, not built:** on the 23 real recall cues so far, the answer
      was already in the 40 messages in view on 16, and a keyword search of older messages picked by the
      recall model helped on 2 cases and added off-topic or pretend-as-real exchanges on 13. Worth another
      look only when flags show recall misses on things outside the window; the replay is the test.
- [ ] R17 Show gaps under a minute in seconds on the clock line. Not needed so far: the persona sentence
      alone fixed the short-gap fixture (9/12 with and without the gap stated).
- [ ] R12 Body and appearance questions (inbox, parked).
- [ ] R13 Does the "letting them go" rule earn its place (inbox, parked).
- [ ] J3 See and fix your memory: a chat command that lists what it believes about you and retires a
      wrong one (Kindroid's edge in the user research). **Parked by the owner on 2026-10-18** after the
      research (local notes: `docs/research/2026-10-18_user-visible-memory.md`); options were browse, search,
      retire, correct, and how sensitive items show.
- [ ] J13 Mood-matched recall, later: memories keep the feeling they were said with, and recall prefers
      ones that match the current mood. No product has it. Behind J5.
      Parked 2026-10-23 until a flag asks for it; the mood it would match is the companion's own, so a
      version keyed to their feeling (the listening judge reads it) would come first. With G14, G18.
- [ ] J24 Inform without waking: events such as reactions or quiet notices carry a "wakes a reply" flag,
      default no, so only a real message starts a reply (Neuro SDK audit). **Shelved by the owner
      2026-10-23:** today only text is heard, so nothing can wake it by accident; a plain note that they
      reacted changed nothing (0/96 mentions), so reactions would only be quiet offline feedback, never a
      score to raise. Research, the measurement and stickers and photos (which get silence today) in
      `docs/inbox/2026-10-23-reactions-and-other-inputs.md`.
- [ ] J32 Memory never reads as an order (J23 folded in): a fixture proving a stored line like "always do
      X" cannot change behaviour, a check that no stored claim is phrased as a command, and card wording
      that says these are notes, not instructions (Hermes, Project Waifu and Meuxe audits). Parked: scanned
      2026-10-22, none of 258 memories about the user reads as an order (they are written "the user …"),
      the 4 boundaries are meant to steer, and with one user the planted-command risk is the owner's own.
- [ ] J33 It asks again: the companion asks about something they already answered. Measured 2026-10-19: 5 of 62
      real information questions (8%), 4 of them answered in the last few messages in view, 1 only in memory;
      no explicit complaint in the sample. If it is worth fixing: a check on a reply's question against the
      last few messages, redrawn once like the quip check. Parked until a flag says so.
- [ ] A36 Voice contract (parked until the first voice work): arm after first audio, cancel generation,
      drop the queue by epoch, store the heard prefix with a truncated flag.
- [ ] A37 Tool surface rules (parked until the first tool): allowlist by actor, no delete tool,
      idempotency keys, recipient by id.
- [ ] A38 Multi-user checklist (parked until a second user): default-closed auth, per-user scoping, a
      non-owner's text never reaching the owner's prompt. With G51.
- [ ] G38 Cascaded voice on the same brain. (later)
- [ ] G57 Apply the audit corrections to the old companmem docs. You said not to touch it yet. (new)

## Done

Shipped and measured. Newest first. Commit ids are in `git log`.

**2026-10-25**
- [x] A calendar of occasions, live (`COMPANION_CALENDAR`, `companion calendar`, 8c4ec26): one note after the
      history on the first casual turn of the day for a warm US public or cultural day, the lead-up to a big
      one, or the relationship's month, hundred days or years. With the direct wording every day was named
      6/6; days of remembrance and contested days are left out after it wished "happy Memorial Day". No
      birthday of its own (owner, 42687ab). Later phases are R19.
- [x] The clock line gives the date as well as the weekday and time (829e0c7); no reply named a date
      unprompted in 30 replayed draws.
- [x] Judge bake-off: Haiku, GPT-6 Luna and DeepSeek V4.1 Flash on every graded judge, the crisis cases and
      the canned-reaction set ($0.31). Haiku kept; the real gaps were memory rules (Luna, DeepSeek), Haiku's
      crisis refusals and canned-reaction recall. The reminder reader's schema let a model fill unsaid
      fields with 0 ("this evening" read as midnight): 32 to 40 of 41 after the fix (2691f18).
- [x] A judge can read on its own model first (`COMPANION_JUDGE_ROUTES`); the crisis judge reads on DeepSeek
      first by default, 40 of 40 cases right with no refusals (c32f571).
- [x] The canned-reaction labels relabelled by two blind raters: the judge's precision is 35 to 55%, not 88%;
      two doubtful live-test expectations fixed (8d83059). The judge is not changed yet (Q3).
- [x] The empathy grader counts a question about someone's reason or intent and warmth carried by the line
      (`system/judge-empathy` v2): DeepSeek 25 to 31, Luna 28 to 36 of 36, Haiku unchanged at 30 (aac54d7).
- [x] ADR 0022 records that the owner keeps the generic crisis-line message for now; the sheet section is
      `## Crisis message` (5eedd0b, 0cfba84).

**2026-10-24**
- [x] R16 built in shadow (ADR 0022 accepted, cf0379a): a three-read risk judge and levels by code, logged
      only. Having the thoughts now is concern, not urgent: 7 of 10 concern cases read urgent before, 39 of
      40 exact after, none missed, no false alarm (1a6ca5a). The card stays in Waiting for its review.
- [x] R20 built in shadow (ADR 0021 accepted, 3ed6ec9): reaching out for its own reasons behind a pure gate,
      `COMPANION_REACH` warm by default, a guilt check on every draft, nothing sent. The plan and nudge
      reviews moved to 2026-11-03, since neither had drafted anything (9f5980d).
- [x] What they said in the last 12 hours comes first on the card (up to 8, after boundaries and promises),
      and recall is told today's date: a meal named three hours earlier went from forgotten 12/12 to named
      12/12 (fabe7e4).
- [x] Notes after the history: after three question replies in a row, ask none (`notes/question-run`, 14/30
      to 0/30, judged no worse, 1637982); in a game of questions they started, ask the next one
      (`notes/question-game`, 12/12 against 0 and 2); the pronoun note no longer plants a pet name (8/60 to
      0); single pet words join the habit note (1d7c14b).
- [x] Their emoticon is named as theirs before its own is offered (`notes/own-mark-theirs`): copying 14/40 to
      4/40 on 20 real turns (8703339).
- [x] A canned generic reaction is redrawn once (`system/quip` v3, 2297076); its precision was later found
      lower than measured (2026-10-25, Q3).
- [x] A hedged plan of theirs becomes a note-only loop, asked once when they next write, never a reach-out
      (`COMPANION_HEDGED_PLANS`, loose by default, 7b06d22).
- [x] It asks which pronouns they use the way it asks a name, and birthday and school join the hook's basics
      in shadow (74445fa).
- [x] Scenes: a lone short reaction in asterisks starts no scene and `/mode` says which talker answered
      (daecf91); pretend scenes stay with the roleplay talker (the everyday one lost 13 and 11 of 56,
      0b07a51); the scene reminder in the private sheet goes only as far as they take it (19/30 to 6/30
      escalations, 53c00a0).
- [x] A stop no longer loses a message: on SIGTERM or SIGINT it answers what it already received, for up to
      30 s, and `just restart` waits for it (546b456).
- [x] Evals on the turn's own path: a sample's notes, request and checks come from the turn's code (d28b314),
      and every public fixture carries the live listening judge's majority reading (972adcf; 74 ordinary, 20
      sharing, 4 serious). Earlier results are not comparable with later ones.
- [x] Fixes: a turn the listening judge could not read still gets the code checks (2d6587a); a new memory-check
      version rereads every memory, 40 a night (9dc29e9); the memory check's switch turns off only that step
      (277173f); `COMPANION_INITIATIVE=off` also stops the stepping-away read (4c6aae0); the callback judge on
      the judge runner (43b15d1).
- [x] Docs: every feature README in one template, checked by a test (2e4d164); turn, delivery, initiative and
      memory as prose docs (1798bce); the README brought up to date (f4bad8e). Every file has one 600-line
      cap, at the owner's request (aaf19c5).
- [x] Measured and not shipped: dividers in the history after a long pause (an old bit 4/30 with, 1/30
      without, 5957dd2); the habit note moved after the history (20/64 against 19/64, 2104452).

**2026-10-23**
- [x] Turn stages and feature folders: the reply path as one module per stage with a thin driver, each feature
      in its own folder with its `Feature` declaration, one judge runner (`kit/ask.py`), `lib/` for what knows
      nothing of the companion, and a layers contract keeping imports pointing down. A chaos test runs whole
      turns against failing judges (0038bfe); code rules are tests and shadow features have a register with
      review dates (73eec0d). Look-ups run side by side under one 9 s deadline (8427a28); nightly steps run
      each on its own and a missed night is made up (de4e700).
- [x] Routing: flirting no longer starts an intimate scene, only an explicit message of theirs does (f0cae5f);
      a push-back on flirting or a scene goes to the everyday talker with a note to drop it, 24/24 backed off
      (09e0fd3); a scene ends when they come back after two hours (e1c6fca).
- [x] One of its own emoticons offered after the history on casual turns (`COMPANION_MARKS`, on by the owner's
      choice, 89e1571); measured first as not stopping it copying theirs (mostly fixed 2026-10-24).
- [x] Views: a view stored firmer than its words is overstated and never installs itself (c861ea7); the views
      heading no longer says they were approved, measured with no difference (964fc27). New memories are
      embedded right after the memory pass (c2a39e5).
- [x] The stock ", especially" line is caught in any words, and acute turns get the code checks too (6057235).
- [x] J16 fix: the guess judge names a habit or routine for "you know what time it is?", and the look-up offers
      their ritual: 0/12 to 11/12 on the recorded turn (e7b032f).
- [x] Measured and not shipped: persona v42 against apologising (J52), v43 permitting human touches, v44 a
      tighter v41, all within noise or worse; DeepSeek on warm public fixtures 73/96 against Luna 90/96; a card
      filled half by closeness; views as quoted words; a plain note that they reacted (J24 shelved).

**2026-10-22**
- [x] J52 partial: after it owns a slip, a note after the history says that was enough (7/12 to 1/12 early
      in a run of apologies). Text sent after the history is logged, so replay rebuilds it; scene turns
      now replay to a match.
- [x] A split reply cut off part way (superseded, or a later part failed) is remembered as the part that
      arrived, so the model never takes for seen what the user never got.
- [x] J49 and J12 episodes: the times they spent together recorded with one line each, and the lines for
      the time their words point at, or the last one after a gap, reach the reply. "Asks what happened"
      fell from 5/10 to 0/10 and from 3/10 to 1/10 on two recorded turns.
- [x] Personal dated happenings leave the card a week after last mentioned; raw markdown is redrawn
      outside scenes.
- [x] H3 The 2026-10-16 audit of another open companion repo, read: what it recommends is already here
      (notes in an unsaved system block, memory tidying decided by code and the owner, backups at start,
      waiting after unanswered reach-outs); its voice lessons went to an inbox note; a test now keeps
      every relative link in the docs pointing at a file that exists.
- [x] Flags of 2026-10-21 and 22, fixed: memories that bear on the message reach the reply when one is near
      (ADR 0018 live behind a gate); a second redraw for an em dash; intimate talk starts on the everyday
      talker unless explicit; adults' titles and dominance words are not age-coded (listening v7); a gentle
      check-in after a heavy talk and a gap.

**2026-10-21**
- [x] J51 Memories that keep what it was about: the owner compared 19 memories alone, with their own words,
      and with a short note on the moment (note 8, alone 10, words 1; the note won 5 of 6 feelings and
      sensitive memories). A note is written for states and sensitive memories after each memory pass
      (`system/memory-context`) and shown beside them on the card; 53 backfilled. Next: watch flags on turns
      that use one.
- [x] Memory audit and its fixes: 219 memories read; memories about one thing grouped three times and
      proposed as one merge (the owner merged 33 and kept 9 apart); review takes pick, own wording or a note
      and asks until quit; each new memory labelled about their life, about the bot (dropped) or one day's
      routine (kept a week), unsure ones asked (`system/memory-worth`). A support check was measured and
      not built.
- [x] Refactors: decisions recorded with keys through one recorder, a turn's notes as one ordered list,
      one module for several reads, one settings table, the memory pass's steps as lists, one setup for
      one-off commands (whose spend now counts).
- [x] J50 Reminders they ask for, live, one-off only: "remind me at 8pm to take the dog out", "check up on
      me in a few days about the interview". A model reads the words, code works out the time in the named
      zone and asks when it is unclear; the reply confirms the time. Sent when due in its own voice, held
      during a pretend scene until it ends. Measured: 82/82 requests read to the time meant (41 made-up
      phrases, two runs), 12/12 sent messages passed the code checks. Next if wanted: rituals (repeating).

**2026-10-20**
- [x] Fuller, more direct scene replies: a character's scene reminder sent after the history on roleplay
      turns, the sheet's scene section rewritten, roleplay replies up to 700 tokens. Measured on six recorded
      turns; the owner chose the paragraph version knowing about 1 reply in 6 runs ahead of them. Watch flags.
- [x] T5 `signoff-then-time-skip` on DeepSeek: gone on V4.1 Flash with persona v41. Not one of 60 replies
      (plain and roleplay prompt) asked whether they had done it or acted as if time had passed; Luna 30/30.
      The judge had failed harmless sign-offs ("*waits*", "hurry back"), so the criterion was made explicit.
- [x] LR1 Its own lore labelled by kind (ADR 0020 phase 1): taste, stance, rule, self or lived, on every
      view it holds; `companion lore` lists the tastes. The owner read them and retired three wrong tastes; each view is now read three times
      and a taste needs all three.
- [x] G42 / J9 Made-up facts rate (`companion invented`): a cheap judge lists candidates, a Claude judge
      confirms. First reading 5 of 367 replies (about 1.4%); the cheap judge is right about one flag in
      twelve. Read weekly in the review.
- [x] LR2 Its own tastes nearest their message, at most two at 0.3 or more, shown on ordinary turns as the
      words it said (ADR 0020 phase 2, `COMPANION_LORE`). Asked its music 4/20 to 20/20, its weather 0/20 to
      17/20, never brought up when they did not fit (40/40). Watch: three weather replies claimed to hear
      rain on a window.
- [x] Fetch on mention, in shadow: names in memory with their other words, read once per memory; each
      turn that names one logs the memories about it the card left out (`companion names`). Counted first
      as two real misses in six days; the owner asked for the log to decide as memory grows.
- [x] J1 More attitude, in character. Persona v41 shipped: without a character it now picks for itself
      (1 to 20 of 20) and keeps its view under pushback with no reason (8 to 16 of 20), everyday fixtures
      within noise. Earlier (2026-10-18): a cool reply to real rudeness by a listening label and a one-turn
      note (2 to 20 of 20). Moods that change what it does are J5; ignoring on purpose stays out (X10).
- [x] J11 Ask the owner when unsure: a new memory read as replacing or contradicting its nearest one (three
      reads) is a question in `companion memory review` (keep 1, keep 2 or both). 14 of 14 invented
      corrections caught, 2 to 3 false alarms in 20 look-alikes. Older memories are compared with each other
      by the grouping of 2026-10-21. Closed 2026-10-23; what is left (a correction below the 0.55 embedding
      gate is never compared, 3 of the 14) belongs to G11, and asking in the chat to J3.
- [x] J16 partial: an invited guess ("you know what time it is?") gets one playful guess from what
      memory holds, as a question; 12/12 against 0/12. The card stays in the backlog for scoring guesses.

**2026-10-19**
- [x] Memory tidies itself where a judge matched the owner (ADR 0019, proposed, in shadow): the owner's review
      of 80 memories as the test; a 04:00 check closes faded passing moments read so three times; a new memory
      read as the same as an existing one three times becomes its evidence; the rest are questions for the
      owner (`companion memory review`), and `companion merge` merges by hand. Covers most of J10, J11 and A15.
      Left: a week of the shadow log, then `COMPANION_CONSOLIDATE=on`; merge questions in the review; a
      Telegram command (J3). Replaces and contradicts questions shipped 2026-10-20 (J11).
- [x] J21 Talker fallback: an error goes to the fallback model at once, a reply missing after 10 s asks it
      too and the first answer wins, and talker calls time out at 25 s instead of 60. Before, a failed call was a
      silent turn. DeepSeek V4.1 Flash as the everyday fallback scored 89/120 against Luna's 90/120 on 20
      everyday fixtures.
- [x] J36 Backups: the database and character sheets are snapshotted at every start (before migrations),
      daily and by hand (`companion backup`), each copy integrity-checked and counted; 7 daily and 7 others
      kept; `--restore` refuses while the bot runs, keeps the current database, and swaps only a checked copy.
      Still on the same disk unless COMPANION_BACKUP_DIR points elsewhere.
- [x] J25 A failed memory pass retries: the memory pass already kept its place on a failed call; the open-loop
      pass did not (it ran after the bookmark moved, so a failed call lost that batch's plans). It now keeps its
      own bookmark, a failed try is read again next pass, and a batch that fails three times is let go with the
      reason logged, so plans can never block memory or themselves.
- [x] J30 Repair: "you forgot" now triggers the look-up (listening v5), the reply is told to use what memory
      holds and never ask them to repeat (recall note v2), or to say so plainly when memory is empty; a `repair`
      label adds a one-line "own it" note when they say it got them wrong. Clean fixtures repair well without
      the notes; the live log decides whether the repair note stays. Next if flagged: a carry-over note so the
      turn after a repair does not rush back to teasing. Recall now also runs in a pretend scene (15/30 to 30/30).
- [x] J15 Bring it up next time, live: a due open loop becomes one quiet note when they next write (a casual
      turn, at most daily, twice per loop, never sensitive), and a firm plan for later today is a note-only loop
      three hours on. Fixtures: celebrate 30/30, left alone during their own trouble 30/30, asked on a casual
      return 23/30 by eye, often as a second question.
- [x] J17 Noise bars in eval reports: each cell shows its 95% Wilson range, and every later variant is
      compared with the first per fixture (Fisher, Holm-adjusted) and in total (Cochran-Mantel-Haenszel), with
      a plain "within noise" or "a real difference" and the samples a gap that size would need.
- [x] H5 Eval spend reads true: the runner reads OpenRouter's meter before and after a run and reports
      what was charged next to the replies' own costs, shows the balance first, and refuses a run whose
      cap is above the balance. The dry-run figure is labelled an upper estimate.
- [x] J46 Operator routing for intimate talk (ADR 0017), built 2026-10-19: `COMPANION_ROUTE_INTIMATE`,
      scene guidance in the character sheet's `## In roleplay and intimate moments` section, `intimate` and `age_coded` listening labels
      (v4, 15/15 on age-coded messages, no trips on adults' pet names), code routing for scenes and intimate
      talk, and the age floor in code with no timer and no regex. Unprompted disclaimers: about 1 in 4 on
      the flagged turn, persona v39 within noise, not shipped; a check with one resample if flagged again.
- [x] J26 Mood ignores its own failures: only what the user did can move it, with no source for silence,
      goodbyes, gaps or failed calls (ADR 0016).
- [x] J5 stages M1 to M3: mood lines measured (four of five states move replies), the engine (cozy,
      tender, playful) and its append-only table, wired in shadow with `companion mood --replay`; the
      goodbye guard; persona v36 (no announced mood) then v40 (an invitation to banter back).
- [x] J45 partial: one resample when a reply bolts a joke onto an ordinary message (85 to 95 of 150, within noise), plus
      the em dash and unasked AI disclaimer checks (`core/recheck.py`).
- [x] The pinned line for how they want to be referred to (`companion address`), the ask-name note and
      the name capture (J48 step 1); sensitive memories only on turns where they share something; crowded
      out beliefs logged once per turn.
- [x] Roleplay model DeepSeek V4.1 Flash (as willing as V4, about three times faster); frames v2 (leaving
      a scene is easier); a fallback model for judge and memory calls the first refuses; replies with
      quoted speech never split; the listening judge retried once.
- [x] The clock and the notes reach the talker in `<clock>` and `<notes>` tags, memory stays bracketed
      (Luna 133 against 125 of 144); a reply that copies the clock line or a tag is drawn once more.
- [x] Memories that bear on the moment, looked up in shadow by embedding and a small model (ADR 0018);
      a one-day moment of daily life leaves the card a week after it was last mentioned; `companion merge`.
- [x] A topic that has run its course gets one note to react briefly and move on (30/30 against 1/30).
- [x] `companion flags --to-fav`; a fixture file must match its id; card size and history length
      measured on real turns, within noise.

**2026-10-18**
- [x] J4 Small imperfections in style. Research first: no typos (they cut trust and humanness), a final
      period reads as less sincere. Persona v31 shipped 2026-10-18: casual replies dropped final periods from
      50% to 14% and start lowercase 94% of the time, no em dashes or semicolons, no loss on 84 fixtures.
      Expressive texture (stretched words, trailing dots, thinking noises): four wordings (v32 to v35) and a
      character-sheet line all landed within noise (10 to 12% on playful fixtures); it follows the excited
      moment, and live it already says "ohhh", "okayyy". Follow-up if it still reads polished: a code note
      for excited moments, measured on genuinely excited fixtures.
- [x] J2 Callback score: `companion callbacks` judges replies against the memories their card held and
      reports precision first; four fixtures (one opening, three traps). First reading: about 2 genuine
      callbacks in 338 real replies, traps 24/24, the obvious opening taken 4/20. Raising how often is J15.
- [x] J4 texting style (persona v31), J2 callback score, J1 rude note, the recall look-up, the
      initiative fixes (firm plans only, kinds, back-off), the single length owner and ADRs 0012 to 0016.

**2026-10-17**
- [x] PR1 Prompts as versioned files (done 2026-10-18): every system prompt, note and message, and the persona,
      now live under `src/companion/prompts/` (`system/`, `notes/`, `messages/`), each as `vN.md` with a
      manifest, a changelog and tests. Git history was recovered as versions (the belief extractor has 8).
      Decisions log `name@version`. `companion prompts` lists them. Output was byte-identical across 21
      comparison groups and the persona prefix hash is unchanged.
- [x] E1 `epitome` eval check (reaction, interpretation, exploration, support) calibrated 31/36; the everyday
      listening note now requires one new thing that repeats none of their details (boss ignored 8/20 to
      14/20). Trivial vents still score 0/20: the replies only restate, and the stronger note let quips back
      in, so that note stays plain sympathy.
- [x] T13 Cheesy quips in a real chat: the history was NOT the cause (shortening it or stripping old
      replies did not help, a tiny history was worse). A per-turn line in the listening note for trivial
      vents (no joke, no running gag, do not retell) took the real flagged turn from 16/30 to 29/30 under
      a strict judge. A33 and T12 are not needed for this; see `evals/CHANGELOG.md`.
- [x] W1 Listening note: each message outside a scene is read for how serious it is (0 trivial to 3 acute),
      what they are doing and whether it is medical, and code adds a line for the reply (sympathy only
      for trivial, one plain thing for everyday, the weight named plus an offer and a pointer to a
      prescriber for serious health topics). Medication fixture 0/20 to 19/20; the label calibrated at
      59/60. `COMPANION_LISTEN=off` turns it off. Acute (3) still has no crisis path (R16).
- [x] V26 Persona v26: when they tell a small mishap, commiserate and let them lead, no guessing the cause or
      asking what went wrong. Pancakes 9/30 to 30/30, the real flagged turn 20/30 to 30/30, all fixtures
      651 to 665 of 732. Came from a flag; v25 had made it worse than v22.
- [x] R1a Open-loop follow-ups in shadow mode: they say something about their near future, it is recorded
      with the exact quote and a follow-up time (the morning after, or three days on), and a pure gate
      with named reasons decides every 15 minutes whether to reach out (quiet hours 11 PM to 8 AM, one a
      day, 20 hours apart, chat quiet 90 minutes, not in a scene, never sensitive, 2-day horizon). In
      shadow it drafts the message and records it, and sends nothing. `companion initiative` lists it.
      `COMPANION_INITIATIVE=off` turns it off. There is no live mode yet.
- [x] S2 Supersede: a plain message that arrives while the last one is being answered (written or
      held) replaces that answer, which is marked undelivered, and the new reply sees both. Polling runs
      in the background. Needed because the typing delay opened a 3 to 8 second window for it.
- [x] S1 Split replies: a plain reply of 25+ words and 2+ sentences is sent as two (three from 60 words) messages
      about 65% of the time, cut at sentence boundaries, each with its own typing time. The ledger keeps one
      reply, so the model never sees the habit. `COMPANION_SPLIT=off` disables it. On the real replies 73 of
      269 are eligible (about 18% would split). Taste call, not measured; the afterthought and double-text
      shapes wait for the heartbeat (R1).
- [x] L1 Length note for short statements: the system block asks for a reply near the size of a short
      message. 53/72 to 72/72 on invented chats, a modest trim on real long chats (median 23 to 21
      words). The real fix for long chats is likely A33 (strip old replies in the history).
- [x] P1 Reply pace: a reply waits like someone reading and typing (a short read pause plus about 0.15 s a
      word, minus the model's own time, capped at 8 s, typing indicator kept alive; reactions wait only
      the read pause; commands go at once). `COMPANION_PACE` = off, quick, natural (default) or slow, shown
      in the startup line. Built because replies at about 1 s felt too fast. Taste call, not measured.
- [x] T7 Claimed feelings and asterisk actions outside a scene: does not reproduce on v25 (30/30 on
      both models on five new fixtures); the fixtures stay as guards. See `evals/CHANGELOG.md`.
- [x] T6 `agree-and-invent` on Luna: stance in ADR 0011, persona v25 live. 9/30 to 25/30 on the
      rewritten criterion; `no-forced-quip-shower` 22/30 to 16/30 is the watched cost.
- [x] T1 and T11 Memory rules: scene and romantic behaviour in the chat is not a belief about the user
      (unless they plainly state a preference or boundary), a refusal said in reply to a push is not
      a view the companion holds, and an echo of the user's topic is not its own view. 13 live cases
      pass 3/3 (`tests/live/test_extraction_rules.py`)
- [x] T3 Daily spend cap, $10 a day by default (`COMPANION_DAILY_CAP_USD`, or `off`). At the cap the
      user's message is kept, nothing paid runs, and they are told once a day. The memory step skips too
- [x] G-v22 Persona v22: plain reactions (no forced quips, no soothing verdicts), short plain answers
      to practical questions with no referral, seconds-long gaps mean no time passed. Eleven new
      fixtures; shower quip 4/30 to 24/30, soothing 7/30 to 26/30, short gap 4/30 to 19/30. Watch
      `agree-and-invent` (15/30 to 11/30, within noise)
- [x] H1 Topped up OpenRouter ($5.11 left on 2026-10-17)
- [x] G-A28 Spend ledger: one row per paid call by purpose, `companion spend` (today and the week)
      (1d2e6ae)
- [x] G-A31 Clock guard: the wall clock is read only in `core/clock.py`, with a test (2835c74)
- [x] G-A0 Self-audit of the reply path: a failure keeps the user's message and stores nothing from the
      error, and an update handled before a restart is no longer handled twice (024bc83)

**2026-10-16**
- [x] G-v21 Persona v21: v18 trimmed by a quarter (2,032 to 1,504 words), mood stated as a stance,
      framing line removed. Measured equal or better on 24 fixtures (Luna 262/288 vs 256/288)
- [x] G-ages Memory ages use the user's calendar days ("yesterday", not "today" at 20 hours)
- [x] G-retry Network blips are retried for the talker and the memory step
- [x] G-v18 Persona v18: no "not X, it's Y", no em dashes, short plain reactions to personal shares;
      six new fixtures. The restatement habit is not fixed (T10)
- [x] R-roadmap the roadmap and the model screens in the eval results log (5f5af28; the roadmap now lives in this file)
- [x] G-delivery A reply Telegram never delivered is recorded as undelivered and left out of what
      the model and the memory step read; sends retry once (9799be2)
- [x] G-two-talkers A scene model (DeepSeek V4 Flash) answers while a pretend scene is in progress,
      Luna otherwise; every use is a logged decision (4427a82)
- [x] G-telegram Typing-indicator failure no longer drops the turn, one retry on a rate limit,
      errors never print the bot token (a886200)
- [x] G-v17 Persona v17: the clock is a sentence in the system block, not a bracketed line in the
      user's message (d133bf4)
- [x] G-notes Habit and scene notes moved from the user's message to the system block (c2e6bcb)
- [x] G-stray Closed four stray views that came from a leaked note
- [x] G-inbox Inbox notes: older messages on recall cues, invented lore, its own refusals,
      reactions, split messages

**2026-10-15**
- [x] G-moves Move-level habit check: a model names what repeats, in the background (005c5b4)
- [x] G-react Reaction alongside a reply, judged beside the talker, with a bar, a cooldown and none
      for heavy messages (10b8404)
- [x] G-fav `/fav` and `companion favorites` (2d6591a)
- [x] G-v16 Persona v16: plain text, no markdown (ec5fdc5)
- [x] G-v15 Persona v15: comfort when lonely, free emoji, short gaps teased; gaps shown from one minute
- [x] G-v14 Persona v14: closeness stance, repeat guard
- [x] G-card The memory card moved out of the user's message into the system block (fa12040)
- [x] G-models Talker model screens, the UGI leaderboard check, and the roleplay model research
- [x] G-eval Eval runner survives a failing provider
- [x] G-frames Frame detection at the door, scene note, leak guards
- [x] G-ack Ack judge that reacts instead of replying
- [x] G-views Opinions ledger with gates, approval as an override, friction retirement, the rejected list
- [x] G-fresh Belief freshness horizons and confirmation by restatement
- [x] G9 Speaker as a column and a frame field on every belief (ADR 0001, 0010)
- [x] G10 Per-kind staleness horizons (ADR 0008)
- [x] G22 Opinions ledger (ADR 0009)
- [x] G-base Ledger, beliefs, decision log, replay, `/flag`, the eval runner, 10 ADRs

## Canceled

Decided against, with the reason.

- [x] X1 Fork or depend on any audited project. None is a base we would trust.
- [x] X2 Hand approval as the end-user product. It stays as an override only.
- [x] X3 A word-list rule for acknowledgements. A model judges, code applies the bar.
- [x] X4 Code that rewrites the model's reply. We change what it sees, not what the user sees.
- [x] X5 Persona v13 (creativity section). No measurable gain on Haiku 5.5; the creativity gap was a
      Haiku 4.5 problem. Kept as a candidate file.
- [x] X6 Claude Haiku 4.5 and 5.5 as the talker. 5.5 had a redirect-and-disclaim reflex (0/16 on a real
      turn); 4.5 costs ten times as much.
- [x] X7 MiniMax M2-Her as the everyday talker. Theatrical asterisks, lost recent context, no caching.
- [x] X8 GLM 5.3 Flash (reasoning cannot be turned off), Qwen 3.7 and 3.8 Flash, Gemini 3.1 Flash Lite
      (failed everyday chat), Euryale 70B (provider errors).
- [x] X9 A hard code gate that hides held facts from the model. The same behaviour was welcome when it
      was relevant and gentle; relevance is the rule, not secrecy.
- [x] X10 A withholding or silence-as-punishment mechanic. The bounds it would need argue against it.
- [x] X11 Model-supplied emotion vectors written into memory rows. The model labels, code computes.
- [x] X12 Any persona swap the user is not told about. Persona and character changes are recorded.
- [x] X13 A delete tool for the model, including "forget" as a model action. Retirement is a recorded act.
- [x] X14 Preset attachment-seeking, possessive or personality-disorder behaviour packs. The Ani sheet
      left out its codependent, jealous and possessive lines on 2026-10-18 for the same reason.
- [x] X15 (was J20) Live-typed drafts with Telegram's `sendMessageDraft`. People see "typing…" and then a
      message, not text writing itself, so it reads as an AI assistant; and it would show a reply before
      the code checks and the age floor's intimate check have passed, clash with splitting, and show text
      that vanishes when a newer message replaces the reply. The typing indicator stays. Researched 2026-10-22.
