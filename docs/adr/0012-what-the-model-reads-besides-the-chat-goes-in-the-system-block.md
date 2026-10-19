# 0012. What the model reads besides the chat goes in the system block

**Status:** accepted 2026-10-18, recording a rule followed since 2026-10-16.

**Context.** Anything inside the user's message can be read as something the user said, and it comes
back in replies. The code wanted to give the talker a clock, the memory card and per-turn notes.

**Decision.** The talker's request is two system blocks and the chat.

- **First block:** the persona, byte-identical turn to turn so it caches.
- **Second block:** everything else the code wants the model to know this turn, built in
  `_assemble` (`loops/fast.py`):
  - the clock line;
  - the name they like to be called, when one is pinned (`notes/address`);
  - the memory card, with held memories only on turns rated severity 1 or more;
  - the notes: habits, scene, length, listening, rude, recall, mood, floor-hold and ask-name.
- **The user's message is sent exactly as typed**, with nothing before or after it. Earlier messages go
  as they were said, minus replies that were never delivered.
- **A new kind of per-turn context goes in the second block.** A feature that needs text in the user's
  message needs a new ADR.

**Why.** Measured on the first three placements:
- The memory card started inside the user message. On three flagged turns (8 samples each, Haiku 5.5),
  replies mentioned held-back facts 8 of 24 times with the card there and 0 of 24 in a system block.
- The clock started as a bracketed line at the top of the user message. On DeepSeek V4 Flash the model
  copied it into replies ("[Friday 02:15] *blink*"). As a plain sentence in the system block (persona
  v17), it stopped.
- Notes in the user message were read as the user's own instructions and answered.

**Consequences.**
- The second block changes every turn, so it is not cached. The persona block and the history are,
  for as long as they do not change.
- The persona describes the second block (the clock line, the memory blocks) so the model knows what it
  is and that the user did not write it.
- `build_request` still accepts a `volatile` text for the user message, because turns recorded before
  this rule carry it and replay must rebuild them byte for byte. Live turns pass it empty.
- Placement stops text being taken as the user's words. It does not stop it being echoed: a note said
  "how heavy it is" and replies said "a heavy feeling to sit with". Note wording is measured for that
  separately (ADR 0014).

**Since:**
- The roleplay talker has its own first block, with the character sheet's scene section (ADR 0017).
  The rule is the same.
- Held memories ride the card only on turns the listening judge rated severity 1 or more (about 7% of
  turns on real history), after a held memory was raised unasked.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) Tagged context inside the user message.

**Reverses if.** A model is found that reliably treats tagged context inside the user message as
not-the-user, and the cache saving matters more than it does now.
