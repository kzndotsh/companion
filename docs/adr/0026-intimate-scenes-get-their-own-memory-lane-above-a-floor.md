# 0026. Intimate scenes get their own memory lane, above a floor in code

**Status:** proposed 2026-10-26. Built in shadow (`COMPANION_SCENE_MEMORY`). Accepted and live (`on` by
default) 2026-11-05, at a review pulled forward from 2026-11-09: 109 logged scene cards read right, and a
flag showed a scene needs what they said about their own body (see "Live" at the end).

**Context.** Intimate talk goes to the roleplay talker under the floor of ADR 0017. On those turns the
roleplay talker gets the same memory card as any other turn: fifteen everyday memories ranked by kind
and recency, with what they said about sex or intimate play mixed in as sensitive, held memories. So a
scene sees their work and their errands, and may miss a limit they stated, while an ordinary chat can
show an intimate preference on a turn where they are sharing something. The memory pass already keeps
what they plainly say about themselves in that setting (`system/extract` marks it romantic and keeps
only stated traits, preferences and boundaries), but nothing keeps how they play inside scenes, and
nothing sorts the two lanes apart.

**The owner's decisions** (2026-10-26):
1. Learn from both: what they say about it outside a scene (the existing extraction) and how they play
   inside scenes. An in-scene pattern counts only once seen in at least two separate scenes, and it is
   only ever shown on scene turns.
2. Scene turns keep a few basics (their name, and how they want to be referred to) besides the intimate
   lane. No other everyday memory.
3. It may bring up something they said they are curious about, not only what they are into. Never a
   limit.

**Decision.**

1. **A lane for every memory, read three times.** A small model places each memory that may be stated
   as true in a lane, everyday or intimate, and gives an intimate one a stance: into, curious, hard
   limit, soft limit, style or aftercare (`system/scene-lane`). It reads each batch three times; a
   memory is intimate only when all three give the same lane and stance. Anything else is kept out of
   scenes as doubt (ADR 0014: models label, code decides). A failed read places nothing. Places are
   append-only and the newest counts (ADR 0002).
2. **A floor in code over every label.** Whatever the reads say, a memory never enters the intimate
   lane when its claim or quote touches age, minors, school or an age-regression headspace (a broad,
   deliberately conservative word check), when it came from a turn the minor check held (ADR 0017), when
   its sensitivity is crisis-level, when it came from a turn read as serious (said while they were
   sharing something heavy), or, for a limit, when it is not in their own plain words (stated, real
   frame, their message). The floor is applied when a memory is placed and again every time a scene card
   is built. `companion scene` shows a memory the floor kept out by its id only.
3. **Patterns from play, never limits.** After each pass, a small model reads each ended scene
   (`system/scene-pattern`) for how they tend to play, each quoted from their own message in play. Code
   keeps one only when the quote is theirs, it is not a limit and nothing in it touches age; a scene
   with a turn the minor check held is never read. A pattern becomes usable only once quoted from two
   separate scenes (decision 1), and only ever reaches a scene card.
4. **The scene card.** On a turn the roleplay talker answers, code builds the memory block as every
   limit (hard first), then at most three (six from 2026-11-02, measured) entries nearest the moment (into, style, aftercare; by
   embedding, as ADR 0018), then at most one curious item, then what they are called. It goes in the
   system block in place of the everyday card, as bracketed text (ADR 0012), with no everyday memory and
   none of its own views. How they want to be referred to stays pinned, as on every turn (decision 2).
5. **A curious item, gated.** The one curious item is marked as something it may invite once, only when
   this turn's brush-off read answered no, and never an item offered in the last three days whose next
   brush-off read said they pushed back. Each offer is logged, which is what the next check reads
   (decision 3).
6. **Everyday turns never show the lane.** With `on`, the memories placed intimate are left off every
   other turn's card, out of what the notes may state as true, and out of the relevance look-up. A memory
   the floor or the reads kept out of scenes stays on the everyday card as before.
7. **Shadow first.** In `shadow` every step runs and logs (the places, the patterns, the scene card it
   would send, the intimate memories it would leave off), and the request is unchanged. `off` does
   nothing.

**Why.** A scene that remembers their limits and how they like to play feels like the same partner from
one night to the next; one that recites their workday does not. Keeping the lane apart also keeps
intimate memories out of ordinary chats. Three reads with code deciding follows the lore labels (ADR
0020), where one read was wrong often enough to matter. The floor is in code, broad and applied twice,
because a label is a request and the floor is the one line no setting or model moves (ADR 0017). A
limit only from their own words, and patterns only after two scenes, keep it from reading too much into
one night's play.

**Consequences.**
- Three small-model calls per batch of 60 unplaced memories each pass, until the backlog is placed, and
  one per ended scene. One embedding call on a turn that may be a scene.
- The broad age check also drops some ordinary adult wording (a bare number under 18, "a little").
  That costs an entry, never a breach.
- The relevance look-up gains a `hidden` set; recall and the other look-ups are unchanged.
- Not doing: inferring a limit from play, bringing up a limit, sending everyday memories into a scene,
  showing a pattern outside a scene.

**Reverses if.** The review finds the logged scene cards wrong often enough (a limit missing, an entry
that does not fit, anything past the floor), or a measured scene fixture shows the scene card loses
care or continuity against today's card.

**Live 2026-11-05.** The review read the 109 scene cards logged since 2026-10-27: the limit was pinned
every time, the nearest entries fit their moments, one gentle offer. A flag the same day showed the
roleplay talker assuming a body the user does not have, with their own words about it in memory but on no
card. Two changes before going live: the basics include memories in which they describe their own body (a
word list in code, never a model; the age floor applies), and the limits and basics are sent after the
history with a heading that asks to keep to them (`notes/scene-basics` v2). On three recorded turns, 12
draws each, the assumed body fell from 21 to 12 of 36 and their own rose from 1 to 12 (`evals/CHANGELOG.md`,
2026-11-05).

_Update 2026-11-07 (the owner):_ memories already placed in the intimate lane stay off every everyday
card and out of both recall look-ups in every mode, not only `on`; reaching out always did. The rule
lives in the turn (`turn/assemble.py`), so `off` keeps them out too.
