# Lessons for a voice mode, if one is built

**Status (2026-10-25):** not built; no voice mode exists, parked until one does, no card.

Added 2026-10-22. An idea, not a task. From the read-only audit of another open companion repo
(local research folder, 2026-10-16), which has voice with barge-in.

- **Store only what was heard.** When the person talks over a reply, keep the part that was played,
  not the whole generated text; otherwise the history holds sentences they never heard, and the
  model later refers to them. That repo stores the generated text; mapping playback position back to
  text is the missing piece.
- **Arm interruption only once audio is flowing.** Talking over a silent "thinking" gap should not
  cancel the turn; cancel only that conversation's stream, never every stream.
- **Echo defence in layers** (headphones, echo cancellation fed with the exact audio played, the
  browser's own), with a short blackout at each onset and a loudness floor.

The same audit's other ideas are already in place here: notes in an unsaved system block after a
stable cached prefix (ADR 0012), nightly memory tidying where code and the owner decide, never the
model alone (ADR 0019), a backup before every start (J36), outreach that waits after unanswered
reach-outs (ADR 0015).
