# Todo

The work board. `docs/ROADMAP.md` keeps the principles, the current state and the measured facts.
This file keeps the cards. Created 2026-10-16.

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

---

## Todo

Ordered. The first three can stop the bot, so they go first.

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


- [ ] T14 Trivial vents have no substance beyond restating a detail (0/20 on the epitome check). Waiting on
      the owner's hand labels of replies across the fixtures (what is unrealistic or cheesy, what he would
      send), then decide whether a short plain sympathy is the right answer or something can be added.

- [ ] T15 Prompt experiments from the guides review (`docs/research/2026-10-18_prompting-guides-review.md`): a
      parrot audit of quoted sample phrases in the persona and notes, a trimmed persona against v26, positive
      rewrites of the notes, a stock-phrase note from the owner's marks, and a read of the Luna model page. Each
      is a prompt version plus a measured eval. Hypotheses only; the sources are mostly assertion. Experiment 1
      (parrot audit) done: persona v28 removes the quoted samples, and only the follow-examples were parroted
      ("scattered", 5 of 6 on the mood fixture to 0); v28 is not live, awaiting the owner's say.

## Doing

- [ ] D1 Watch the two-talker setup in real chat (Luna for everyday, DeepSeek V4 Flash for scenes).
      Split `/flag` and `/fav` by the model that wrote each turn. Done when a week of marks shows
      whether the scene model helps and where the voice change at the boundary hurts.

## Done

Shipped and measured. Newest first. Commit ids are in `git log`.

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
- [x] R-roadmap `docs/ROADMAP.md` and the model screens in the eval results log (5f5af28)
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

---

## Decisions needed from the user

1. **Pacing (T2):** evidence-based, the user dial ("quick", "natural", "slow burn"), or both? What is
   the default friction?
2. **Intimacy limits:** where the character's own pace ends and the model's hard limits begin, and how
   a model refusal is shown.
3. **Body and appearance question** (inbox, parked since the start).
4. **Provider routing (T8).**
5. **Flagged turns in history (T9).**

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

### H. Product and business

- [ ] G51 A second user, which exposes everything tuned to the first. (new)
- [ ] G52 Wellbeing design: pushing toward people, crisis and disclosure protocols in character.
      (partial)
- [ ] G53 Regulatory fit: disclosure laws, an adults-only gate, a consent record. No audited project
      has a working consent layer. (new)
- [ ] G55 Extract the memory engine as its own product. Long term. (new)
- [ ] G56 A side-by-side harness comparing our memory with others behind one interface. (new)
- [ ] G57 Apply the audit corrections to the old companmem docs. You said not to touch it yet. (new)
