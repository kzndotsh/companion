# 0014. Models label, and code chooses the note

**Status:** accepted 2026-10-18, recording the pattern behind the listening, length, scene and habit
notes.

**Decision.** When the talker should behave differently this turn, a small model or a plain rule
produces labels, and code turns the labels into a fixed note from `prompts/notes/` (ADR 0013).
- Listening: a judge labels severity (0 to 3), stance, vague and medical; code picks the trivial,
  everyday or serious note, adds the health line and the offer to talk, and gives no note at
  severity 3.
- Length: code counts the words they wrote and adds a limit for a short statement, never for a
  question, a scene or a serious message.
- Scene: the stored frame of the previous turn (ADR 0010) picks the play, story or hypothetical note.
- Habits: a judge names repeated moves and code counts repeated openers and phrases; code decides
  whether to add the note.
- Every choice is logged as a decision whose reason is built from the labels (ADR 0003, 0006).

**Why.** A model writing its own instruction for the next model is an unlogged, untestable decision
in free text. Labels are small, checkable and can be calibrated against hand labels (the listening
judge matched 59 of 60). Fixed notes can be tested, measured in evals with the same `+listen` or
`+len` switch the live code uses, and changed one version at a time. Structural rules (no length cap
on a serious message, no note at severity 3) live in code, where a test holds them.

**Consequences.**
- Adding a behaviour means a label, a rule in `core/` and a note file, with tests for the rule.
- Notes combine. Code owns the combinations: when two notes would conflict (the length cap and the
  serious note did), the fix is a rule in code, not more note text.
- The habit note quotes the judge's short description of the habit. That text is model-written; it is
  capped at 90 characters and only describes, it never instructs.
- A judge that fails or times out means no note, never a guessed one, and the reply still goes out.
- Note wording is still read by the talker and can be parroted, so notes are measured like prompts.

**Reverses if.** One model can label and reply in a single call as reliably, and the saving in
latency or cost outweighs losing the separate log of why.
