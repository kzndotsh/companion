# Persona versions

Each version is a new file. The prefix hash on every turn record says which one a turn used.

- **v1.** First draft. Long replies, a question nearly every turn.
- **v2.** Added: the clock line, short-reply rule, question rule, use-what-you-know, no unprompted
  counselling, no claimed introspection, and five example exchanges. Fixed the failures in the
  first transcript.
- **v3.** v2 minus the example exchanges. Reason: the owner did not want to hand it sample replies
  to copy. An ablation (30 replies per variant, 15 turns) showed the examples moved length and
  imperatives very little (median 14 words either way), so little is lost.
- **v4.** v3 plus a "What you remember" section explaining the state card: a block of beliefs after
  the clock line, and a second block of sensitive ones to hold unless the user raises them.
  Reason: the first transcript showed it ignoring what it had been told, and the card is how
  beliefs reach the reply.
- **v5.** v4 plus one sentence in "What you remember": the memory block is neutral, "the user" is
  the person and "the companion" is you. Stored beliefs stay in the neutral voice so any reader
  (a person, another companion after a model swap, the engine on a non-companion product) can
  follow them. Reason: a belief read "the user started building the companion" and nothing told
  the companion it meant itself.
- **v6.** v5 plus a first-person rule under "What you can honestly say about yourself": say I and
  me, never "the companion". Reason: flagged `off` on the first card turn ("it spoke about the
  companion rather than itself"). Replay showed the card was delivered correctly and the model
  used it, but phrased the project as a third party. The v5 key explained the word; this rule
  governs how it talks.
