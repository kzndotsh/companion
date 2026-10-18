# Prompt assembly changes

What the model is sent besides the persona text, and how that has changed: where the memory card
and notes sit, how the clock is shown, how memory ages are worded, what the history window leaves
out, and which model answers. These are code changes, so they are not versions of the persona, but
they change how the persona is read. Newest last. The clock moving into the system block went with
persona v17; see [CHANGELOG.md](CHANGELOG.md).

- **Memory card moved out of the user message.** The card is now a system block after the
  persona. Reason: on three flagged turns (8 samples each, Haiku 5.5) replies mentioned
  held-back facts 8 of 24 times with the card inside the user message and 0 of 24 with it in a
  system block (judged OK 14/24 vs 18/24; crude regex, one conversation). Known leftover: v12
  still says the memory block "follows the clock line". Reword it in the next persona version
  and measure that with the same three turns.

- **Repeated-phrase note.** `core/habits.py` now also counts word runs (3 to 5 words, starting
  and ending on a real word) that recur in the last six replies, and tells the next turn to say
  something different. Counts only, no topic knowledge. Check on the ledger: it fired on 5 of 12
  turns of the asterisk-roleplay chat and 0 of 56 turns of the earlier ordinary chat. Effect on
  replayed turns (GPT-6 Luna, 8 samples on each of 5 turns where it fired): a model judge called
  the reply a repeat of an earlier gesture or move 27/40 times without the note and 18/40 with
  it. Exact phrases were not reused either way, so the loop is in the move ("tucks the blanket
  around you"), not the words; the note helps but does not end it.

- **Move-level habit note.** After each reply, in the background, a small model reads the last
  six replies and names up to three things that repeat: a pet name, an emoji, a sentence shape,
  a gesture in new words (`core/moves.py`, `loops/moves.py`). The next two turns get a note
  describing them and asking for something different. Checked on 8 replayed turns from a long
  roleplay (GPT-6 Luna, 6 samples each): it named the real habits (hand at the waist, a smirking
  emoji, "sweetheart", "menace", kisses as the go-to move); "sweetheart" went from 18 to 1 of 48
  replies, the smirking emoji from 10 to 4, and a judge calling the reply a repeat of its
  earlier shape, name or emoji from 45 to 33 of 48. The scene's own format (action in asterisks
  then a quoted line) is still named and still repeated, since the user writes that way too.
  Replaces nothing: the cheap word-run note in `core/habits.py` still runs.

- **Habit check fix.** The move-level check sometimes listed non-habits ("no repeated pet
  names", "not a consistent pattern"). The model must now give, for each habit, how many of the
  replies it appears in, and code drops any seen in fewer than three.

- **Notes moved out of the user message.** The habit note and the scene note used to ride the
  user's message next to the clock line. A live chat on DeepSeek V4 Flash showed the model
  reading the habit note as something the user said: it apologised for "a habit of reaching for
  the same kind of phrase", said "that's a good note", and the memory step even recorded a "self
  preference" from that reply. Replaying six of those turns (8 samples each): replies that
  leaked the note or echoed the bracketed clock line were 7 to 8 of 48 with the notes in the
  user message, 2 to 4 of 48 with the notes in the system block beside the memory card, and 1 of
  48 with the clock moved there too. The notes are now in the system block. The clock is still
  in the user message, which needs a persona change (the persona describes it there).

- **Two talkers.** While a pretend scene is in progress (the previous turn was tagged `play`),
  replies come from a scene model, DeepSeek V4 Flash by default; everything else comes from the
  everyday model, GPT-6 Luna by default. `COMPANION_SCENE_MODEL=none` turns the split off, and
  `COMPANION_MODEL` still sets the everyday model. The first message of a scene is answered by
  the everyday model, because the frame is only known after the message. Reason: on the same
  persona, Luna led everyday chat (59/64 on the public fixtures against DeepSeek's 49/64) while
  DeepSeek kept a scripted scene going more (76% against 52% of escalating turns). Every use of
  the scene talker is a logged decision, and each turn's record names the model that replied.

- **Undelivered replies are left out of what the model reads.** A reply is stored as soon as it
  is written, before Telegram delivers it. When delivery fails the user never saw it, but the
  model would read it as said and carry on from it, and the memory step could learn views from
  it. A reply that fails to arrive is now recorded in an append-only table and skipped by both
  the history window and the memory step, and the decision is logged. Replay stays consistent
  because the record is written before the next turn.

- **Memory ages are the user's calendar days.** The card said "(mentioned today)" for anything
  supported less than 24 hours ago, so something said at 6 pm yesterday read as "today" at 4 pm.
  The companion repeated it ("you did, earlier today") and the user flagged "time awareness is
  thrown off regarding its memory". The age is now the difference in local calendar days
  (`when_phrase` in `core/freshness.py`, same zone as the clock line): today, yesterday, N days
  ago. Checked on the live data: the "flirt" belief (last said Thursday 18:52) changed from
  "today" to "yesterday".

- **A length note for short statements.** Replies to short casual statements ran three to four
  times longer than the message (a 4-word message got a median of 15 words, 2026-10-17). When
  their message is a statement of 12 words or fewer, with no question mark, and no scene is in
  progress, the system block gets one line: "[Their message was short (N words), so keep your reply
  short too, under about X words, unless what they said needs more.]", with X about one and a half
  times N plus four, never under 8. `core/length.py`. It never appears in a scene, for a question
  or for a long message. On 6 invented short statements, 12 samples each: 53/72 checks without it,
  72/72 with it. On 22 real turns replayed with their long histories: median 23 to 21 words and
  replies over 25 words 49/132 to 37/132, checks 152/264 to 158/264, within noise. No leak of the
  note's wording and no curt replies on a read by eye.

- **A listening note, chosen from how serious a message is.** Before the reply, a small model
  (Haiku 5.5, `core/listening.py`, `loops/listen.py`) labels each message outside a scene: severity 0
  trivial, 1 everyday friction, 2 serious personal, 3 acute; what they are doing (listening, inviting
  a view, other); whether they were vague about what is wrong; whether it is medical. Code turns the
  labels into one line for the system block. Severity 0 listening: sympathy only, no advice, no
  question about the cause, no joke, pun, running gag or clever comparison, no picking up an image
  they used and no retelling of what they said. Severity 1: react first in their register, then one new thing that repeats none of their details: a plain fact, a
  gentle suggestion on their side or a single question about reasons or intent (an offer to talk if
  vague). Severity 2: name the weight in plain words, no advice on what to do or on treatment, no
  interpreting, an offer to talk it through, and under about 35 words; if medical and they have not
  said they are in care, say once that a prescriber or a doctor can help. Severity 3 gets no note:
  there is no crisis path yet (R16) and the decision log says so. The offer is not repeated within
  four replies. The ack and listening judges now run before the talker starts, so an ack no longer
  wastes a talker call, and a turn waits for the judge (about a second, absorbed by the reply pace).
  `COMPANION_LISTEN=off` turns it off. Calibration on 20 invented messages, 3 runs each
  (`tests/live/test_listening_judge.py`): severity exact 59/60, stance 56/60, medical 6/6, and no
  serious message read as trivial.
