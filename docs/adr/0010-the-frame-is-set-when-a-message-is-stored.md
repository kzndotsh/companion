# 0010. The frame of a message is set when it is stored

**Status:** accepted 2026-10-15.

**Decision.** Every utterance is stored with its frame: real, play, story, hypothetical, or out of
character. Utterances are append-only (ADR 0002), so the frame is decided before the row is written.

- A cheap check for cues (pretend, imagine, "what if", asterisk actions) decides whether a small model
  is asked at all. A scene already in progress is assumed to continue and also asks. Most messages
  never reach a model.
- The model runs beside the reply, like the acknowledgement judge (ADR 0006): it labels the frame
  with a confidence, code applies a threshold (0.70, otherwise real), and the reason that is logged is
  built by code from the scores.
- The companion's reply takes the user's frame when it is play, a story or a what-if (it plays along)
  and is real otherwise. Stepping out of character ends the scene for both.
- A scene in progress adds a one-line note to the next reply, taken from the previous turn's stored
  frame, so it does not wait for the judge.
- "Play" means pretend or fiction. A game of honest questions is real, and its answers become
  beliefs like any other.

**Why.** The belief rules already refuse a sincere fact from a play, story or hypothetical frame
(ADR 0001), and across 80 repositories none had a frame field. But the field was always `real`,
because nothing set it, so the protection did nothing. Setting it at the door makes the existing
rules work with no schema change.

**Where play is kept out.** Beliefs from a non-real frame, or said as a joke or in pretend, are
recorded but are never shown to the companion as facts (`is_assertable`). The companion's own lines
inside a scene are never taken as its views. The extraction prompts mark which messages are pretend.

**Consequences.**
- On 14 hand-labelled messages the real model stored the expected frame 12 times. The two misses are
  defensible: a virtual hug in a real emotional moment read as real, and "ok you got me" in a detective
  scene read as stepping out. Every case that matters was right, including a game of honest questions
  (real) and a tease inside a pretend scene (play).
- A judge that times out (2.5 s) stores real, so a failure leaks pretend into memory as real rather than
  losing the user's message. Real is the safer error for a message whose frame is unclear.
- The judge is a model and can be wrong. Every judgement is logged with its scores, so it can be
  checked against use.
- Game state (whose turn it is, what was just asked) is separate and not built yet.

**Reverses if.** The judge's errors prove costly in either direction, or a cheaper rule matches it.
