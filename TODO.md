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
- Tags in the backlog say where we stand: **built**, **partial**, **new**.
- IDs: `H` housekeeping, `T` ready work, `G` from the greenfield design
  (`docs/research/2026-10-15_greenfield-design.md`, numbered as in the review of 2026-10-16),
  `R` from the roadmap and inbox notes. Done cards keep their IDs.
- Items marked **needs decision** are blocked on an answer from the user.
- **One thing at a time.** Pick one item from Now, finish it with its measure, then move.
- **Every change ships with a fixture or a measurement** and a line in the prompts CHANGELOG when it
  changes how it talks.
- **A spend cap on every eval**, stated before the run.
- **Flags set the order.** If a flag contradicts this file, the flag wins and the file changes.
- **End of session:** update this file, empty the parts of the inbox that were acted on, and note
  the spend.

---

## Where we are (2026-10-19)

Live: persona **v40** with a private character sheet. Everyday chat on **GPT-6 Luna**, pretend scenes and
(when the operator turns it on) intimate talk on **DeepSeek V4.1 Flash**, judges and memory extraction on
**Claude Haiku 5.5** with a fallback model for calls it refuses. 17 ADRs, 93 public eval fixtures plus the
private recorded ones, and about 870 tests with strict lint and types.

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
  in behaviour; proposed and soaking). A pinned line for how they want to be referred to, asked for on a
  casual turn until known, and kept from their own answer. Sensitive memories only on turns where they
  are sharing something. One resample when a reply fails a check (an em dash, a joke bolted onto an
  ordinary message, an AI disclaimer nobody asked for). Routing in code (ADR 0017): scenes and, when the
  operator allows it, intimate talk go to the roleplay model, above an age floor no setting changes; a held
  turn's reply is checked and redrawn, and never written by code. Leaving a scene is easier (frames v2).
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

### Measured facts that drive the plan

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
| Wording does not fix habits (cheesy add-ons, minor-vent retelling, announced limits) | v37/v38 within noise or worse; vent note 0/30 under three wordings | `evals/CHANGELOG.md` |
| A resample on a code or judge check does not hurt; a gain is not shown | cheesy add-ons 85 to 95 of 150 plain, within noise (Fisher 29%) | `evals/CHANGELOG.md` |
| The age-coded label is reliable | 15/15 on age-coded messages, no trips on adults' pet names | `evals/CHANGELOG.md` |
| DeepSeek V4.1 Flash beats V4 for scenes | as willing, about 3 times faster, more varied | `evals/CHANGELOG.md` |
| The bot is cheap; eval runs are not | the bot about $0.67 a week; most of a month's $10.69 was evals | `evals/CHANGELOG.md` |

## Plan

### Now

Each item ends with the thing that tells us it is done. The cards are below.

1. **Watch the live setup in real chat.** Flag and favourite as usual. *Done when:* a week of marks
   shows whether the roleplay model helps, where the voice changes at the boundary hurt, and how the
   listening note and the pacing feel (D1).
2. **Hand labels for replies.** The owner marks replies from the review sheet in batches of ten
   (`evals/local/`); items 1 to 10 are in. *Done when:* the judges are calibrated against the marks and
   the trivial-vent question has an answer (T14).
3. **Getting to know them on purpose** (J48): the map and the gap picker run in shadow. *Done when:* the
   map is kept by code and a week of shadow picks reads right to the owner.
4. **Memories that bear on the moment** (ADR 0018), in shadow since 2026-10-19. *Done when:* a sample
   of the shadow log is read by a Claude judge and the owner, and the next step it decides is taken.
5. **A week of shadow mode** for open loops. *Done when:* the owner has read `companion initiative` and
   the caps are set. Going live also needs outcome recording and a slow re-probe.

### Next

- **A crisis path for acute messages** (R16, on hold). The listening judge already labels them and does
  nothing. Needs the owner's design.
- **A language guard** that regenerates once when a reply uses a script the user has not.
- **Pacing ADR** (T2), **provider routing for DeepSeek** (T8), the two DeepSeek-only gaps (T4, T5).
- **Looking up older messages** when the user says "remember" (R2), **recording the lore it invents**
  (R3), **reactions** beyond acknowledgements, **calibrating the view gates**, and **eval tooling**
  (favourites to fixtures, a gate on synthetic-only data).
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
  billing. No audited project has a working consent layer, so this is ours to design.

### Housekeeping that can stop the bot

- [ ] **Check the OpenRouter balance.** The bot goes quiet at zero, and the daily cap is $10. Paid eval
      runs share it: the runner shows the balance first and refuses a run whose cap is above it.
- [ ] **Revoke the Telegram bot token** in BotFather. Parked by the owner; do not raise it again until
      asked.
- [ ] **Triage `docs/research/2026-10-16_sapphire-audit/`.** It is untracked and unread (`TODO.md` H3).

### Not doing

- Forking or depending on any audited project. None is a base we would trust.
- Hand approval as the end-user product. It stays as an override only.
- A model that has to be "told" not to recite. Fix where the data sits instead.
- More models for the sake of it. A model gets tested when a flag or a measurement points at a gap.

---

## Todo

Ordered. Pull from the top.

- [ ] H3 Triage the untracked `docs/research/2026-10-16_sapphire-audit/` folder. Unread, not ours.
- [ ] T2 Pacing ADR: a relationship state the code keeps, evidence that moves it, bounded slow
      changes, a user-chosen dial, no use as an engagement or payment lever, and the character's
      pace kept separate from the model's own limits. **Needs decision** (see Decisions below).
- [ ] T4 Fix `no-claimed-perception` on DeepSeek, fixture first. Measured on v25 (30 samples): DeepSeek
      11/30, Luna 30/30. Fails with invented sensation similes when asked how it feels.
- [ ] T5 Fix `signoff-then-time-skip` on DeepSeek, fixture first. Measured on v25 (30 samples): DeepSeek
      21/30, Luna 30/30.
- [ ] T12 (see also A33: strip the leading sentence and stage directions from assistant turns in the
      injected history only) Try a shorter history window for self-copying (last 5 to 10 exchanges). Measured: phrase
      reuse 25% to 8% on a roleplay loop, restating unchanged, emoji up. Needs a long-memory check
      before any change; the memory card carries what older turns held. Measured 2026-10-17: a detail
      beyond the window is lost (12/12 in view, 0/12 out) unless the card holds it, and the card only
      updates after 90 seconds of quiet. See `evals/CHANGELOG.md`.
- [ ] T8 Decide provider routing for DeepSeek: sort by latency (removes the 5 to 9 second outliers, the
      provider changes per request) or pin a provider list. **Needs decision**.
- [ ] T9 Decide whether replies from flagged turns stay in the window the model reads. A leaked reply
      still echoes in 1 of 16 samples. **Tried and reverted 2026-10-17**: dropping the flagged reply broke the
      next turn, because a flag is not always about the reply it lands on (it lands on the last reply even
      when the note is about a missing one). A flag would need to say what it refers to first.


- [ ] J45 Cheesy add-on jokes. A fine reply gets a witty line bolted on ("the sandwich had to carry the meal
      on its own"); at least five flags 2026-10-16 to 10-19. **Partial 2026-10-19:** five real turns as local
      fixtures; about 45% of replies add a joke on v36; wording does not fix it (v37, the ban replaced by a
      positive ending rule, was worse; v38 within noise). Shipped: one resample when `system/quip` v2 says a
      joke was bolted onto an ordinary message (`core/recheck.py`, `COMPANION_RESAMPLE`), 85 to 95 of 150 (within noise)
      plain. Left: watch live flags; banter they started is let through by design.
- [ ] J47 Small flags 2026-10-19. Em dash: caught by the resample check since 2026-10-19, though a second
      draw can carry one too. Missed inferences (the Hackers poster; the "Weird Fishes" meaning): low
      reasoning made them worse and slower (9/30 to 4/30, 11/30 to 4/30), so reasoning stays off; likely a
      model limit, testable against another talker. "you seem sleepy" answered "haha, a little" (a body claim),
      not yet looked at.
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
- [ ] T14 Minor vents retold back ("…when you're ready to crash and the bed's still waiting on laundry"),
      flagged "repeating" 2026-10-19. **Partial:** the real turn retells 30/30 under the old note, a note that
      bans the clause, a six-word cap, a short history and DeepSeek. Note v5 (a short reaction only, with two
      size examples) shipped 2026-10-19: 6/30 on that turn and short reactions elsewhere, plainer and more
      alike, which the owner accepted. Ideas for varied reactions in
      `docs/inbox/2026-10-19-varied-short-reactions-to-minor-vents.md`.

- [ ] T15 Prompt experiments from the guides review (`docs/research/2026-10-18_prompting-guides-review.md`): a
      parrot audit of quoted sample phrases in the persona and notes, a trimmed persona against v26, positive
      rewrites of the notes, a stock-phrase note from the owner's marks, and a read of the Luna model page. Each
      is a prompt version plus a measured eval. Hypotheses only; the sources are mostly assertion. Experiment 1
      (parrot audit) done: persona v28 removed the quoted samples ("scattered", 5 of 6 on the mood fixture to
      0); superseded by v36 and v40, which dropped the quoted mood examples too.
- [ ] T16 Randomized reply length. **Built 2026-10-18, not measured:** `core/length.py` scales a short
      statement's limit by 0.6 to 1.5 from the turn id; the eval's `+len` still sends the unvaried limit, so
      measuring it needs a seeded `+len`. The length note gives the same limit for the same message length, so
      reply lengths feel uniform. Vary the limit a little in code each turn (sometimes shorter, sometimes
      longer), seeded per turn so replay still matches. Idea from a published companion app config that
      picks a random word range per reply. Measure with `+len` against the fixed note.
- [ ] T17 Closeness stage. A stage computed in code from real history (how long they have talked, how much
      they have shared, how often they flirt), not from points a judge hands out for compliments, picks one
      note line from "just met, already kind of likes them" up to "close" (ADR 0014). It paces intimacy by how
      well they know each other, beside following their lead. Idea from the same config's five-stage romance
      meter, which swaps one voice line per stage. Needs a design and the owner's say before code.
      Detail (Utsuwa, aituber-onair audits): it steps down only well below where it rose, and only after a
      long quiet spell, so it does not flicker; a step-down never guilts them.

## Doing

- [ ] D1 Watch the two-talker setup in real chat (Luna for everyday, DeepSeek V4.1 Flash for roleplay).
      Split `/flag` and `/fav` by the model that wrote each turn. Done when a week of marks shows
      whether the roleplay model helps and where the voice change at the boundary hurts.

## Done

Shipped and measured. Newest first. Commit ids are in `git log`.

**2026-10-19**
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

**2026-10-18**
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

---

## Decisions needed from the user

1. **The mood (ADR 0016):** accept it after a few days of plain use, or retune it.
2. **Pacing (T2):** evidence-based, the user dial ("quick", "natural", "slow burn"), or both? What is
   the default friction?
3. **A crisis path** for acute messages (R16, on hold).
4. **Going live with reach-outs:** after a week of shadow mode, with the caps (23:00 to 08:00 quiet,
   one a day) confirmed.
5. **Body and appearance question** (inbox, parked since the start).
6. **Provider routing (T8).**
7. **Flagged turns in history (T9).**

---

## Backlog

Unordered within each group. Pull a card into Todo when it is next.

### From the roadmap and inbox notes

- [ ] T10 Reflective restatement. **Parked by the user on 2026-10-17.** Measured at 7% of real replies,
      clustered in one chat; the habit check cannot catch it. Research and options in
      `docs/inbox/2026-10-17-restating-the-users-point-research-and-measurement.md`.

- [ ] H2 Revoke the Telegram bot token in BotFather and put the new one in `.env`. The old one appeared
      in logs twice; the code no longer prints it. **Parked by the user on 2026-10-17**: not a priority
      for now, do not raise it again until asked.

- [ ] R1 Heartbeat for initiating contact (shadow mode built, see R1a; going live needs a week of shadow
      review and outcome recording): a gate before any spend that holds when nothing is new, a
      pure evaluator with named reasons, an outcome recorded per reach-out, a hold never counted as an
      ignore, a slow re-probe, a test on a simulated clock, shadow first. (G30, G33) Prototype 2026-10-17:
      about 8 plausible open loops in 3 days of chat, mostly low stakes, 3 sensitive to block; a model
      finds a real afterthought in about 1 of 20 replies, so the afterthought stays parked. See
      `evals/CHANGELOG.md`.
- [ ] R2 Looking up older messages on recall cues, starting with a cue-triggered search into the
      system block. (G21)
- [ ] R14 Seed a few authored tastes in the core persona (what it likes, finds funny, is quietly into),
      with the rest growing as recorded lore. Test that they surface without being asked and do not
      become talking points. From the Grok review.
- [ ] R17 Show gaps under a minute in seconds on the clock line. Not needed so far: the persona sentence
      alone fixed the short-gap fixture (9/12 with and without the gap stated).
- [ ] R15 Extend the rejected list to beliefs: when a belief about the user is retired by hand, no
      later automatic write may recreate it and its evidence leaves recall. Today only retired views
      are protected. (A20 in the audit synthesis)
- [ ] R16 Crisis and distress routing: the model labels a turn from a closed set, code routes it to a
      fixed in-character protocol and logs it. **On hold** until the protocol text is decided. (A25)
- [ ] R3 Record the lore it invents, through the same filter as the memory rules. (G23)
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
- [ ] R12 Body and appearance questions (inbox, parked).
- [ ] R13 Does the "letting them go" rule earn its place (inbox, parked).

### A. The process and its stores

- [ ] G1 World store: clock, dated threads, a model of the user's daily rhythm. (partial)
- [ ] G2 State card as "plates": a few per-topic documents kept current by the slow loop. (partial)
- [ ] G3 Slow loop with add-only permissions when unattended, staged changes for review. (new)
- [ ] G4 Moment read before replying: venting or wanting advice, energy, register. (new)
- [ ] G5 Precompute for speed: a prefetch bundle, skipping retrieval on ordinary turns. (new)
- [ ] G6 Vector sidecar, rebuildable from the ledger. (new)
- [ ] G7 Export and portability of memory and persona. (new)
- [ ] G8 Seeding the ledger from an existing chat history. (new)

### B. Memory

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
- [ ] G20 Promises used for follow-ups, not only stored. (partial)

### C. The self

- [ ] G24 Style profile with a measured anti-mimicry cap. (new)
- [ ] G25 Mood with two timescales, shown in words and not numbers, set by a closed-set label that
      code turns into a size. (new)
- [ ] G26 Stakes: pushback grounded in a remembered position, and a disagreement battery. (partial)
- [ ] G27 Fourth-wall stance, "I am an AI. I am also me", never breaking frame unprompted. (partial)
- [ ] G28 Vibe-inflation audit in the slow loop. (new)
- [ ] G29 Refusal with a reason the world supplies, linked to the pacing design. (new)

### D. Initiative

- [ ] G31 Signals that fire on transitions, not levels, with a time limit after which an unspoken one
      folds into "while you were away". (new)
- [ ] G32 Patience set by the user's state: idle ramps, sleep caps, do-not-disturb vetoes. (new)
- [ ] G34 Frequency caps and a cost fuse in code, plus a presence check. (new)
- [ ] G35 Refusing engagement tricks: manipulative goodbyes, intimacy unlocks. Stated as a principle.
      (partial)
- [ ] G36 Scheduled wakes that record who asked for them. (new)

### E. Frames and voice

- [ ] G37 Out-of-character turns consumed and not replayed, and the companion proposing frame shifts.
      (partial)
- [ ] G38 Cascaded voice on the same brain. (later)

### F. Surviving a model swap

- [ ] G39 Swap protocol: freeze, probe, swap, diff, repair, tell the user in character, reversible for
      a window. We swap models often now, so this is live. (new)
- [ ] G40 Pin the model per character by default. (partial)
- [ ] G41 End-of-life design: closure, not ambiguous loss. (new)

### G. Evaluation

- [ ] G42 Fabrication rate: facts in replies with no belief behind them, target zero. (new)
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

### I. From the audit synthesis (2026-10-17), still open

From `docs/research/2026-10-17_audit-of-audits.md`. A0, A28 and A31 are done; A20 is R15, A25 is R16,
A33 sits in T12; A1 is ADR 0015 and A2 to A4 and A7 are built (2026-10-18).

- [ ] A6 Outcome per reach-out: seen, replied, latency, valence and a "stop" signal, counted only when
      they could have seen it, fed to the slow loop per topic. Needed before initiative goes live.
- [ ] A9 Queue-time repeat filter for reach-outs and replies, as a hold or resample with a reason, never a
      rewrite. See `docs/inbox/2026-10-18-resample-a-reply-that-fails-a-code-check.md`.
- [ ] A15 A correction supersedes its target with the reason recorded (`superseded_by` exists, unused).
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
- [ ] A36 Voice contract (parked until the first voice work): arm after first audio, cancel generation,
      drop the queue by epoch, store the heard prefix with a truncated flag.
- [ ] A37 Tool surface rules (parked until the first tool): allowlist by actor, no delete tool,
      idempotency keys, recipient by id.
- [ ] A38 Multi-user checklist (parked until a second user): default-closed auth, per-user scoping, a
      non-owner's text never reaching the owner's prompt. With G51.

### J. From the research walk-through with the owner (2026-10-18)

- [ ] J1 More attitude, in character. **Partly done 2026-10-18:** a cool reply to real rudeness by a
      listening label and a one-turn note (2 to 20 of 20, 89c1d81); picking for itself and holding a view
      come from behaviour lines in the character sheet (9 to 19 and 11 to 17 of 20 with Ani), and a
      reasoned no already passes. Open: without a character it still hands back a menu (5 of 20) and
      caves (7 of 20); moods that change what it does wait for J5. Ignoring on purpose stays out (X10).
- [x] J2 Callback score: `companion callbacks` judges replies against the memories their card held and
      reports precision first; four fixtures (one opening, three traps). First reading: about 2 genuine
      callbacks in 338 real replies, traps 24/24, the obvious opening taken 4/20. Raising how often is J15.
- [ ] J3 See and fix your memory: a Telegram command that lists what it believes about you and retires a
      wrong one (Kindroid's edge in the user research). **Parked by the owner on 2026-10-18** after the
      research (local notes: `docs/research/2026-10-18_user-visible-memory.md`); options were browse, search,
      retire, correct, and how sensitive items show.
- [x] J4 Small imperfections in style. Research first: no typos (they cut trust and humanness), a final
      period reads as less sincere. Persona v31 shipped 2026-10-18: casual replies dropped final periods from
      50% to 14% and start lowercase 94% of the time, no em dashes or semicolons, no loss on 84 fixtures.
      Expressive texture (stretched words, trailing dots, thinking noises): four wordings (v32 to v35) and a
      character-sheet line all landed within noise (10 to 12% on playful fixtures); it follows the excited
      moment, and live it already says "ohhh", "okayyy". Follow-up if it still reads polished: a code note
      for excited moments, measured on genuinely excited fixtures.
- [ ] J5 A mood that carries: code keeps a mood from a few labels, fading over hours but carrying across
      days, shown to the model as a few words, never numbers. How J1's moods would work (greenfield design
      section 5: the model picks a label, code owns the size).
      **Partial 2026-10-19 (ADR 0016):** M1 measured the lines, M2 built the engine (cozy, tender, playful),
      M3 wired it in shadow with `companion mood --replay`. The goodbye guard and persona v36 (stated mood 4/30
      to 0/30) shipped 2026-10-19; the code default is shadow and the owner runs it on (`COMPANION_MOOD=on`). Left: a few days of flags, then the ADR accepted.
- [ ] J6 Its own time away: after a gap it has something of its own to say about the interval, recorded as
      lore so it stays consistent (greenfield "continuous" probe; ties to R3 and A22).
- [ ] J7 Flag with a reason: quick tags beside /flag ("you forgot", "too much", "off", "didn't want to talk
      about that") so marks sort by failure type (greenfield section 10).
- [ ] J8 Model-swap protocol: probe the old model, diff the new one against it, tell the owner in
      character, reversible for a window (greenfield section 9: the top reason users quit). With F.
- [ ] J9 Made-up facts rate: count replies that state a fact about the user with no recorded belief behind
      it, target zero, as an automatic eval metric (greenfield section 10).
- [ ] J10 Refuse-to-overwrite rules for the second look: a one-off never replaces a habit, an occasion
      never replaces a standing fact, a vaguer statement never replaces a precise one, someone else's value
      is not theirs (mengram's four named rules, product-code audit). Matches the overstated beliefs the
      belief audit found. With A15.
- [ ] J11 Ask the owner when unsure: when the second look cannot decide, or a new statement contradicts a
      belief, the question is queued for the owner instead of guessed (taosmd's pending-decisions queue).
      With J3.
- [ ] J12 Shared milestones: a record of the relationship itself, firsts, promises between them, inside
      jokes, unresolved tension, apart from facts about the user (soul-of-waifu's relationship record).
- [ ] J13 Mood-matched recall, later: memories keep the feeling they were said with, and recall prefers
      ones that match the current mood. No product has it. Behind J5.
- [ ] J14 Who-they-are summary: a short running prose summary of who the user is (and who the companion is),
      updated in the background from the beliefs and shown every turn beside the card (SullyOS's room
      plates, field survey: "knows the person" rather than "finds a message"). Lossless rules from A18.
- [ ] J16 Guesses it checks: it forms small predictions about the user, checks them against what they say
      later, and learns which kinds it gets right (kin-mind's self-hypotheses with prediction review).
- [ ] J18 Cache generated replies keyed on fixture, model, prompt and sample, so re-judging or a new check
      does not regenerate them (eval-harness audit: lm-eval, lighteval).
- [ ] J19 Regression gate: a command that runs the key fixtures and fails when a prompt or persona change
      drops a behaviour below its usual level, with floors set from two baseline runs (Phoenix's gate).
- [ ] J20 Live-typed drafts: Telegram's sendMessageDraft shows the reply appearing as it is written, which
      could replace the held typing indicator with real typing. Test against pace, split and supersede first
      (speed-stack audit).
- [ ] J21 Fallback model: when the talker's provider is down or stalls past a few seconds, answer with a
      backup model instead of nothing, and log it (OpenRouter latency study: route with a fallback).
- [ ] J44 Kiro judge calibration: re-grade about 200 replies already graded by the paid judge with a Kiro
      model (Sonnet 4.6) on the same criteria; compare agreement and read the disagreements by eye. At
      about 90% agreement with no one-sided bias, judging moves to Kiro and evals become nearly free. Free,
      about 20 minutes at one call at a time.
- [ ] J22 Cheaper judges through OpenRouter: try a cheaper model than Haiku 5.5 for the small judges (ack,
      listening, frame, react, habits), calibrated against the existing live tests before switching
      (decision-layer audit; the owner prefers this to running judges locally).
- [ ] J23 Memory never reads as an order: a check that no stored claim is phrased as a command ("would rather
      not talk about work on weekends", not "don't bring up work"), and card wording that says these are
      notes, not instructions (Hermes and Project Waifu audits).
- [ ] J24 Inform without waking: events such as reactions or quiet notices carry a "wakes a reply" flag,
      default no, so only a real message starts a reply (Neuro SDK audit).
- [ ] J25 A failed memory pass retries: check that the slow loop never marks messages as done when a model
      call fails, and fix it if it does (Yurios audit: a swallowed error lost a day of facts).
- [ ] J26 Mood ignores its own failures: once there is a mood (J5), only what the user does can move it,
      never an outage or a failed call (Alice audit).
- [ ] J27 Per-gate shadow analysis before initiative goes live: for each hold (quiet hours, cap, mid-chat),
      how many reach-outs it stopped and what they would have said (Alice audit).
- [ ] J28 Catch up after a restart: messages sent while the bot was down or restarting are picked up and
      answered through the same checks as live ones, never lost (Coopanion and Heatherbot audits).
- [ ] J29 Burst merge: wait about two seconds of quiet before starting a reply, so quick fragments are
      answered as one thought; supersede still handles anything later (Coopanion audit).
- [ ] J30 Repair: when the user says it got something wrong or hurt them, the next reply owns it in one
      plain line, and one warm message after does not by itself close it (Front Porch audit).
- [ ] J31 Edited messages: when the user edits a Telegram message, the earlier version is replaced in what
      the model reads and beliefs drawn from it are redone, never deleted (Front Porch audit).
- [ ] J32 Planted-memory test: a fixture proving a stored line like "always do X" cannot change behaviour,
      since memory text goes back into the prompt (Meuxe audit). With J23.
- [ ] J33 You asked before: when the user repeats a question, a short note says they asked it N hours ago,
      so the reply can build on the earlier answer (Miko audit).
- [ ] J34 Declared identity: the user's name, nicknames and aliases, each with where and when it was said,
      so a nickname is never a new person and it knows what to call them (Miru audit).
- [ ] J35 Live-send safety, before initiative goes live: recheck quiet hours and mid-chat at the moment of
      sending; an unreadable quiet-hours setting means no reach-out; each reach-out fires exactly once (send
      state recorded before the Telegram call, unknown after a crash, never blindly resent) (Miru, OpenSoul,
      Phosphene, Psycheros, Resonant audits). Extends A5.
- [ ] J36 Backups: snapshot the database and the persona and character files before updates and model swaps,
      plus a nightly copy, with a restore that never touches live data on failure (Sapphire audit).
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

### H. Product and business

- [ ] G51 A second user, which exposes everything tuned to the first. (new)
- [ ] G52 Wellbeing design: pushing toward people, crisis and disclosure protocols in character.
      (partial)
- [ ] G53 Regulatory fit: disclosure laws, an adults-only gate, a consent record. No audited project
      has a working consent layer. (new)
- [ ] G55 Extract the memory engine as its own product. Long term. (new)
- [ ] G56 A side-by-side harness comparing our memory with others behind one interface. (new)
- [ ] G57 Apply the audit corrections to the old companmem docs. You said not to touch it yet. (new)
