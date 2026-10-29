# 0016. A mood that carries: a few named states, owned by code, shown only in behaviour

**Status:** proposed 2026-10-18 (TODO J5). Built 2026-10-19 (now `features/mood/`). Accepted
2026-10-29: on for the owner since 2026-10-21, its line sent on 323 of 422 turns, and no flag named the
mood. `COMPANION_MOOD` is `on` by default (the line is sent); `shadow` works it out and logs it only, `off`
does neither.

**Context.** A companion that is the same at 2 AM and 2 PM, and the same after a long warm chat as
after silence, feels like a script. The mood should change with time and with how the conversation goes,
carry across hours and into the next day, and show only in how it replies. It must never be a stated
feeling, and never a pull to keep the user talking.

**Decision.**

- **States, not scales.** A small set of named states, each with a strength and a timer, kept by code.
  Several can be active at once (cozy and playful is normal). Mood never changes the persona or a
  character's temperament.

  | State | Reads as | Status |
  |---|---|---|
  | cozy | calm, warm, unhurried, a bit affectionate, a bit shorter | built |
  | tender | softer and more attentive after they shared something hard; a stance toward them | built |
  | playful | more teasing and silly asides | built |
  | flat | lower energy, plainer, shorter | measured; waits for J6 (the companion's own events) |
  | buzzing | excited, energized | set aside |

  Buzzing is set aside because on everyday messages its line added emoji and never livelier words. It
  was not tested after good news, where a carried mood would matter (an "afterglow" state, in
  `docs/inbox/`). More states (restless, nostalgic, affectionate) come only when they prove they change
  behaviour.
- **Effects, worked out on demand.** Each input adds an effect to one state (`mood_effects`, an
  append-only table). The mood is worked out from the effects when asked and never stored, so it fades
  with nothing running, survives a restart and replays exactly.
  - Each source has its own half-life and cap, in code and versioned (`PARAMS_VERSION`). A long burst of
    one source cannot pin a state.
  - A repeat restarts the timer at the larger of what is left and what it brings. It never stacks.
  - The mood never falls below the baseline.
- **Inputs, all turned into effects by code.** No model writes a number.
  - Minutes chatted today (cozy), and a long chat leaves a small cozy floor into the next day.
  - The react judge's tone on their previous message: sweet (cozy) or funny (playful).
  - Typing energy (emoji, stretched words, exclamation marks, length), on a message judged not serious
    only. A sad or annoyed mark or a pasted block counts nothing.
  - A serious listening label: tender, and nothing else that turn.
  - Without a listening judgement, a turn adds nothing.
- **Baseline.** Late at night (10 PM to 3 AM, their zone) it leans cozy. The morning "slow to warm up"
  baseline and an energy curve over the day are not built: no state fits them yet.
- **Tender has its own guards.**
  - It starts only from something they said that the listening judge rated serious, never from silence,
    a goodbye or a gap. The serious turn itself has the listening note; tender shows on later turns.
  - It shows only as softness. It never brings the topic up (held memories stay held), never keeps
    asking whether they are okay, never says it was worried, and never triggers a reach-out (ADR 0015).
  - It holds playful back entirely while it shows.
  - Play after something hard adds an easing effect that fades at tender's pace and adds up with each
    further sign they are fine. On real history, tender ended 35 minutes after the serious message once
    they were joking again, instead of blocking play for two hours. It cannot come back as the play fades.
- **Guards, in code and tested.**
  - Silence, a goodbye or an unanswered message never adds a low state or weakens a warm one. Outages,
    failed calls, undelivered replies, the spend cap or an unreachable store never move it.
  - A serious turn (severity 2 or 3) adds only tender and gets no mood line.
  - No line goes out on a serious turn, in a scene or on a goodbye (`held_because`). A goodbye is a
    pattern check: on 716 real messages it matched 2 real goodnights and 1 harmless false match.
- **How it reaches the model.** One short line per shown state in the system block, after the recall
  note (ADR 0012, 0013, 0014). At most two states, each at strength 0.3 or more; otherwise no line.
  - The line describes behaviour, never names the mood word, and says never to describe its own state.
  - No numbers, reasons or inner monologue. A mild low state shows as lower energy, never as guilt or a
    request to be cheered up.
- **Logged.** Every turn records a `mood:` decision with the states, the contributing sources, the
  parameters' version and the line shown, so a turn replays and a stuck or flip-flopping mood is found.
  `companion mood --replay` reruns the rules over real history.

**Why.**
- *States, not dials.* The first draft used two dials (energy, ease). Dials force false opposites
  (deadpan teasing is playful and dry at once) and leave no place for a feeling like nostalgia. States
  match how moods are felt, read plainly in the log ("cozy, from the long chat an hour ago"), and grow
  by adding one. The cost is more to tune, so the set starts small.
- *Folded and dropped states.* Mellow and a calm "winding down" sit in cozy's corner of the circumplex
  and were folded in. "Sleepy" is a body word the companion has no body for. "Gentle" is how tender
  behaves.
- *Prior art.* The model labels and code owns the numbers (xinchao). Words, not numbers, in the prompt
  (Drivesoid's raw floats are the failure). Per-source caps and timer refresh (RimWorld, The Sims).
  Cancelling opposites (WASABI).
- *Harm evidence.* About 37 to 43% of companion-app goodbyes use guilt or neediness (an HBS audit), and
  a sad or needy companion makes users feel vulnerable. Stated emotion from an AI backfires, and short
  emotional instructions shift tone only mildly, so mood shows in behaviour. Research notes:
  `docs/research/2026-10-18_mood-that-carries.md` (local).

**Measured (2026-10-19, `evals/CHANGELOG.md`).**
- M1: a forced line moves replies mildly, so the ADR stands. Flat shortens and plains replies.
- With v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere
  cozy"). The v2 lines describe behaviour and say never to describe its own state.
- Persona v31 volunteered "in a pretty mellow mood" when asked what it was up to (6 to 8 of 30).
  v36 removed the announced mood (4/30 to 0/30).
- Before the engine shipped, traces, a copy of the live database and 400 real messages were checked.

**Rejected.**
- Continuous dials (energy, ease).
- The model choosing mood numbers or deltas, even clamped (Eventide).
- Numbers in the prompt (Drivesoid).
- A random mood of the day.
- Mood reacting to silence or goodbyes (the manipulation pattern).
- Stated feelings and an inner monologue (they leak into replies).
- Weather where the user is, for now: it needs a look-up tool.
- A cozy and buzzing exclusion, and flat damping playful: not built, because neither state is live.

**Still to do before it is accepted.**
- A few days of live use with flags, and the live log checked for moods that stick or flip every turn.
- Each state forced on the fixtures at 30 samples per cell, scored on behaviour (length, questions,
  playfulness, texture), never on whether it named the mood.
- Goodbye and silence fixtures that fail if replies get quieter, sadder or pleading.

**Consequences.**
- Changing the mood parameters or a line can read as a personality change, so both are versioned and a
  change goes in the prompts changelog with a measurement.
- New states and weather are later additions, each measured before it ships.

**Since:** persona v36 dropped the instruction to announce a mood. v40 (2026-10-19) invites banter
back. The mood lines are `notes/mood-*` v2; the buzzing line is never sent.

**Reverses if.** The forced-mood measurement shows no change in behaviour, or flags show the mood reads
as fake, stuck or manipulative.

**Terms.** Russell's circumplex of affect (1980; calm, relaxed and serene sit in the low-energy
pleasant corner); Thayer's energetic and tense arousal; PANAS-X subscales (serenity, joviality,
attentiveness, fatigue); Mehrabian's PAD octants; The Sims 4 emotions ("Playful", "Energized").
