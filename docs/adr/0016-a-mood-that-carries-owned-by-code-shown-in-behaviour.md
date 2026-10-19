# 0016. A mood that carries: a few named states, owned by code, shown only in behaviour

**Status:** proposed 2026-10-18 (TODO J5). Nothing is built yet; this records the design and its rules
before any code, as the audits advise for anything with state.

**Decision.** The companion has a mood that changes with time and with how the conversation goes, carries
across hours and into the next day, and shows only in how it replies.

- **State.** A small set of named states, each with a strength and a timer, kept by code. The first six:
  sleepy, mellow, cozy, playful, buzzing and flat. Several can be active at once (sleepy and cozy is
  normal); a few real opposites exclude each other (sleepy and buzzing cannot both be strong; flat damps
  playful and buzzing), the way The Sims stops the low and high version of a mood stacking. More states
  (restless, nostalgic, affectionate) are added only when they prove they change behaviour. Mood never
  changes the persona or a character's temperament.
- **Why states, not scales.** The first draft used two dials (energy, ease). Dials force false opposites
  (deadpan teasing is playful and dry at once) and leave no place for a feeling like nostalgia; states match
  how moods are felt, read plainly in the log ("cozy, from the long chat an hour ago"), and grow by adding
  one state instead of redesigning axes. The cost is more to tune and measure, so the set starts small.
- **Baseline.** The time of day sets gentle background states (sleepy late at night, mellow early in the
  morning) that the rest add to; never a different person.
- **Inputs, all turned into effects by code.** Minutes chatted today; the user's texting energy in a message
  (emoji, stretched words, exclamation marks, length), carried over only on the positive side (toward
  playful or buzzing, never mirroring distress); tone labels the existing judges already give (funny,
  flirty, sad) and the listening severity; later, the companion's own small events (J6). No model writes a
  number.
- **Effects.** Each input adds strength to a state with its own duration. Each source has its own cap, so
  one long burst of hype cannot pin a state; a repeat refreshes the timer instead of stacking; effects that
  pull in opposite directions in the same stretch cancel first. Strength fades with a half-life of about
  three to five hours of real time, a setting, back to the baseline. A long good stretch leaves a small cozy
  floor into the next day; an intense warm stretch biases the next few hours.
- **Guards, in code and tested.** Silence, a goodbye or an unanswered message never adds a low state or weakens a warm one,
  and decay toward the baseline never takes it below the baseline. Outages, failed calls, undelivered
  replies, the spend cap or an unreachable store never move it. A turn the listening judge rates serious
  (severity 2 or 3) freezes every state and gets no mood line. Mood never appears at a goodbye to keep them
  talking.
- **How it reaches the model.** One short line in the system block, a versioned prompt like the other
  notes (ADR 0012, 0013, 0014): the strongest one or two states in plain words, each with the concrete
  behaviour that goes with it (sleepy: shorter replies, fewer questions, let quiet sit), and never to say
  it. When no state is strong enough there is no line. No numbers, no
  reasons, no inner monologue. Mild negatives are allowed (tired, flat, a bit off) and show as lower
  energy, never as guilt or a request to be cheered up.
- **Logged.** Every change records the states before and after, the contributing effects, the mood
  parameters' version and the line shown, so a turn can be replayed and a stuck or flip-flopping mood found.

**Why.** Prior art agrees on the shape: the model labels and code owns the numbers (xinchao), words not
numbers in the prompt (Drivesoid's raw floats are the failure), per-source caps and timer refresh
(RimWorld, The Sims), cancellation of opposites (WASABI). The guards come from the evidence on harm: about
37 to 43% of companion-app goodbyes use guilt or neediness (an HBS audit), and a sad or needy companion
makes users feel vulnerable. Showing mood in behaviour, not stated feelings, follows the research that
stated emotion from an AI backfires and that short emotional instructions shift tone only mildly. Research
notes: `docs/research/2026-10-18_mood-that-carries.md` (local).

**Rejected.**
- Continuous dials (energy, ease): they force false opposites; see "Why states".
- The model choosing mood numbers or deltas, even clamped (Eventide).
- Numbers in the prompt (Drivesoid).
- A random mood of the day (the owner declined it).
- Mood reacting to silence or goodbyes (the manipulation pattern).
- Stated feelings and an inner monologue (they leak into replies).
- Weather where the user is, for now: it needs a look-up tool.

**How it will be measured.** Each state forced on the fixtures, 30 samples per cell, scored only on
behaviour (length, questions, playfulness, texture), never on whether it named the mood; goodbye and
silence fixtures that fail if replies get quieter, sadder or pleading; the live log checked for moods that
stick or flip every turn; the time-of-day baseline checked against the owner's own logs before tuning.

**Consequences.**
- Changing the mood parameters or the line can read as a personality change, so both are versioned and a
  change goes in the prompts changelog with a measurement.
- New states and weather are later additions, each measured before it ships.

**Reverses if.** The forced-mood measurement shows no change in behaviour, or the owner's flags show the
mood reads as fake, stuck or manipulative.
