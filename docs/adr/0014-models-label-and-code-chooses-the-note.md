# 0014. Models label, and code chooses the note

**Status:** accepted 2026-10-18, recording the pattern behind the listening, length, scene and habit
notes. It now also covers recall, rude, mood, floor-hold and ask-name notes, and routing (ADR 0017).

**Context.** When the talker should behave differently this turn, something has to tell it. A model
writing its own instruction for the next model is an unlogged, untestable decision in free text.

**Decision.** A small model or a plain rule produces labels, and code turns the labels into a fixed
note from `prompts/notes/` (ADR 0013).

- **Listening.** One judge (`system/listening`, v4, one retry on a miss) labels each message outside a
  scene:
  - severity 0 to 3, stance, vague, medical;
  - rude, and recall with a topic;
  - intimate and age_coded, which only route (ADR 0017).

  Code picks the trivial, everyday or serious note, adds the health line and the offer to talk, adds the
  rude or recall note, and gives no note at severity 3.
- **Length.** Code counts the words they wrote. A short statement gets a limit. A serious message
  (severity 2) gets a fixed target. A question, a scene and an acute message get none.
- **Scene.** The stored frame of the previous turn (ADR 0010) picks the play, story or hypothetical note.
- **Habits.** A judge names repeated moves, and code counts repeated openers and phrases and decides
  whether to add the note.
- **Mood.** Code works out the mood from effects and adds a line only above a strength bar (ADR 0016).
- **Floor-hold and ask-name.** Code adds them from its own rules. Floor-hold is the held-turn note of
  ADR 0017. Ask-name goes on a casual turn when no name is known, at most once a day.
- **Every choice is logged** as a decision whose reason is built from the labels (ADR 0003, 0006).

**Why.** Labels are small, checkable and can be calibrated against hand labels. Fixed notes can be
tested, measured in evals with the same `+listen` or `+len` switch the live code uses, and changed one
version at a time. Structural rules (no word cap on an acute message, no note at severity 3) live in
code, where a test holds them.

**Measured.** The listening judge matched 59 of 60 hand labels on severity (v1; stance 56/60, medical
6/6). Later labels were measured when they were added (`evals/CHANGELOG.md`).

**Consequences.**
- Adding a behaviour means a label, a rule in `core/` and a note file, with tests for the rule.
- Notes combine, and code owns the combinations. When two notes would conflict (the length cap and the
  serious note did), the fix is a rule in code, not more note text.
- The habit note quotes the judge's short description of the habit. That text is model-written, capped
  at 90 characters, and only describes, never instructs.
- A judge that fails or times out means no note, never a guessed one, and the reply still goes out. The
  listening judge gets one retry first, because a missing reading also costs the recall and the route.
- Note wording is still read by the talker and can be parroted, so notes are measured like prompts.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) A model writing the note text. Letting one model label and reply in a single call.

**Reverses if.** One model can label and reply in a single call as reliably, and the saving in latency
or cost outweighs losing the separate log of why.
