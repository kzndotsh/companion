# 0025. Its own history is canon lore, checked against the sheet before it is kept

**Status:** proposed 2026-10-26. Step 1 (capture, the canon check and a logged look-up, all in shadow)
is built. It is read at the review of 2026-11-09 (`core/shadows.py`), which decides step 2.

**Context.** In chat the companion makes up small details of its own past: a stray cat it once named, a
haircut it regrets, a habit from when it was younger. Nothing keeps them, so the next day it may name the
cat differently or forget it had one. ADR 0020 kept its tastes as lore and labelled the odd claim of a
lived event `lived`, never lore. But the views ledger hardly sees these stories. `system/self-extract`
drops anything said in a pretend scene and anything it says it felt or experienced, which covers most of
a story about its past. A character sheet, when one is set, already gives an authored past, so a new
story can be checked against it. Research behind ADR 0020 applies here too: personas drift within a few
rounds, and checking a new line against earlier ones cuts contradictions (Dialogue NLI, DECODE,
measured).

**The owner's decisions** (2026-10-26):
1. Only stories it makes up while chatting. No generated "life between chats".
2. In a pretend scene, a small fact about itself said in passing counts (a stray it once named). What
   happens inside the scene's story does not.
3. Small everyday details only for now: a pet, a haircut, a habit, a small memory. A big life event (a
   past partner, family, a trauma, a death, an illness) is never canon unless the sheet already has it.

**Decision.**

1. **Its own store, not the views.** A story is a quoted detail of its own past with the message's frame,
   kept in its own append-only tables (`features/history`), apart from the views ledger and from
   anything about the user. Nothing enters without a quote, a speaker and a frame (ADR 0001, 0010).
2. **Captured from its own messages, scenes included.** A small model reads its messages after the
   history's own bookmark (`system/history-capture`) and labels each detail as its own past or as part of
   the scene. Code keeps a detail only when the quote is in one of its own messages, the message is not a
   what-if, and the label is its own past (decision 2).
3. **Checked before it is canon.** Each new story is read three times against the sheet and the stories
   already canon (`system/history-canon`): fits, same, contradicts, too big or not a story. Code decides.
   Canon needs no read to object. The same story told again becomes evidence of the first, not a second
   story. A contradicting or too-big story is never canon and keeps its reason (decision 3). A failed
   read rules nothing and the story waits.
4. **Nothing is deleted.** Each ruling and each owner retire is an event; the newest is the standing
   (ADR 0002). `companion history` lists them and `companion retire ID` retires one.
5. **Shown only when the moment touches it, later.** Step 1 logs, on an ordinary turn, the canon stories
   nearest their message (embedding, as ADR 0018 and 0020), with how often each was told and whether a
   telling is still in the messages the talker reads. Step 2, after the review, may show them as a note
   that says it told them before, so it keeps to them instead of retelling them as new.

**Why.** A story is the kind of detail that drifts most, and the one a person notices when it changes. A
check against the sheet is what makes the sheet the canon of its past instead of a starting point it
contradicts. Keeping stories apart from the views keeps the views' gates (said on two days, real frame
only) as they are, since a story is said once and often in a scene. Three reads with code deciding
follows the lore labels (ADR 0020), where one read put advice among its tastes.

**Consequences.**
- One more small-model call per memory pass that has its own messages, and three per new story. On a
  first run it reads the whole chat from the start, three batches per pass.
- ADR 0020 still never counts a `lived` view as lore. History is where its past lives; a lived view is
  not moved into it.
- Not doing: generated off-screen activities, big life events not in the sheet, anything about a body or
  senses beyond what the sheet and persona allow, rewriting what it said.

**Reverses if.** The review finds the rulings wrong often enough that the owner would rather keep a
hand-written list, or step 2 shows no gain in consistency on a fixture that asks about its past on
different days.
