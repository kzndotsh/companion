# 0012. What the model reads besides the chat goes in the system block

**Status:** accepted 2026-10-18, recording a rule followed since 2026-10-16.

**Decision.** The talker's request has two system blocks and the chat. The first block is the
persona, byte-identical turn to turn so it caches. The second holds everything else the code wants
the model to know this turn: the clock line, the memory card and the notes (habits, scene, length,
listening). The user's message is sent exactly as they typed it, with nothing added before or after
it. Earlier messages in the history are sent as they were said, minus replies that were never
delivered.

**Why.** Anything inside the user's message can be read as something the user said, and it comes
back in replies.
- The memory card started inside the user message. On three flagged turns (8 samples each, Haiku
  5.5), replies mentioned held-back facts 8 of 24 times with the card there and 0 of 24 with it in a
  system block.
- The clock started as a bracketed line at the top of the user message. On DeepSeek V4 Flash the
  model copied it into replies ("[Friday 02:15] *blink*"). Moved into the system block as a plain
  sentence (persona v17), it stopped.
- Notes in the user message were read as the user's own instructions and answered.

**Consequences.**
- A new kind of per-turn context goes in the second block. A feature that needs to put text in the
  user's message needs a new ADR.
- The second block changes every turn, so it is not cached. The persona block and the history are,
  for as long as they do not change.
- The persona describes the second block (the clock line, the memory blocks) so the model knows what
  it is and that the user did not write it.
- `build_request` still accepts a `volatile` text for the user message, because turns recorded before
  this rule carry it and replay must rebuild them byte for byte. Live turns pass it empty.
- Text in the system block can still be copied into replies (a note said "how heavy it is" and
  replies said "a heavy feeling to sit with"). Placement stops it being taken as the user's words, not
  stops it being echoed; note wording is measured for that separately.

**Reverses if.** A model is found that reliably treats tagged context inside the user message as
not-the-user, and the cache saving matters more than it does now.
