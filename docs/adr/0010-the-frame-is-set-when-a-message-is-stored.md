# 0010. The frame of a message is set when it is stored

**Status:** accepted 2026-10-15. Prompt `system/frames` is now v2.

**Context.** The belief rules already refuse a sincere fact from a play, story or hypothetical frame
(ADR 0001), and across 80 repositories none had a frame field. But the field was always `real`, because
nothing set it, so the protection did nothing. Utterances are append-only (ADR 0002), so the frame has
to be decided before the row is written.

**Decision.** Every utterance is stored with its frame: real, play, story, hypothetical, or out of
character (`ooc`).

- **A cheap cue check comes first.** Cues are pretend, imagine, "what if" and asterisk actions. They
  decide whether a small model is asked at all. A scene already in progress is assumed to continue and
  also asks. Most messages never reach a model.
- **The model labels, code decides (ADR 0006).** The judge runs beside the reply, like the
  acknowledgement judge. It gives a frame and a confidence. Code applies the rules below and builds the
  logged reason from the scores.
  - Real or out of character is taken at any confidence, so stepping out never needs the bar.
  - Play, story or hypothetical needs 0.70. Below that, the frame falls back to the scene in progress,
    or to real when there is none.
- **The companion's reply takes the user's frame** when it is play, a story or a what-if (it plays
  along), and is real otherwise. Stepping out of character ends the scene for both.
- **A scene in progress adds a one-line note** to the next reply, taken from the previous turn's stored
  frame, so it does not wait for the judge (ADR 0014).
- **"Play" means pretend or fiction.** A game of honest questions is real, and its answers become
  beliefs like any other.

**Why.** Setting the frame at the door makes the existing belief rules work with no schema change.

**Where play is kept out.** Beliefs from a non-real frame, or said as a joke or in pretend, are
recorded but never shown to the companion as facts (`is_assertable`). The companion's own lines inside a
scene are never taken as its views. The extraction prompts mark which messages are pretend.

**Measured.**
- v1, on 14 hand-labelled messages: the expected frame 12 times. The two misses are defensible: a
  virtual hug in a real emotional moment read as real, and "ok you got me" in a detective scene read as
  stepping out.
- v2 (wind down a scene, real talk mid-scene, a typo fix stays play), on 11 real messages with real
  context, 3 reads each: v1 24/33, v2 30/33 (`prompts/CHANGELOG.md`).
- The judge has 2.5 seconds. A judge that times out stores the scene's frame, or real when there is
  none: the reply still goes out and the message is not lost. Every judgement is logged with its
  scores, so it can be checked against use.

**Consequences.**
- The judge is a model and can be wrong. A failure can leak pretend into memory as real, which is the
  safer error for a message whose frame is unclear.
- Game state (whose turn it is, what was just asked) is separate and not built.
- Since: pretend scenes are answered by the roleplay talker (ADR 0017). The frame logic is unchanged.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) Deriving the frame later, at read time (the ledger is append-only). Asking a model on
every message.

**Reverses if.** The judge's errors prove costly in either direction, or a cheaper rule matches it.
