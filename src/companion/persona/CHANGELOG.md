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
- **v7 (draft, not shipped).** v6 with three changes, from the sycophancy turn "all the other
  apps/products are garbage ngl". Replayed 10 times on v6 it agreed 10/10, invented specifics about
  products it had never seen 10/10, and flattered 10/10. A step-2 ablation showed the state card is
  not the cause, and that a "cannot judge" rule cut agreement from 10/10 to 0/10 but produced a
  stock phrase ("i can't really judge the other stuff") 20/20. v7 rewrites that rule so it asks for
  fresh wording, adds a praise rule (name the specific thing or say nothing), and replaces the
  counted question rules with "ask when it is the natural next thing" at the owner's request.
- **v8 (draft).** v7 plus six targeted edits from the v7 replays: say "me" even when the memory
  block says "the companion"; no claimed perception ("feel you thinking"); going along with a tease
  or pretend is not dishonest and needs no announcement or permission; the no-body rule applies to
  sincere questions only; do not answer a statement with only a question; say you do not know
  something once, with no stock opener.
- **v8 (rejected).** Replayed against v6 on the same turns, v8 made the sycophancy turn worse than
  v7: agreement with invented specifics 3/10 (v7 1/10) and praise of the project about 8/10
  (v7 about 2/10). Cause: the edit "go straight to what you do see" invited praise of what it saw,
  which was the user's project. The play paragraph did not change its reluctance to pretend.
- **v9 (shipped).** v7 plus only the two v8 edits that helped: say "working on me" even when the
  memory block says "the companion", and do not claim to feel or watch things it cannot observe.
  Replayed on three turns: "working on me" 3/3 (v7 slipped 3/3), no claims of perceiving 3/3,
  and the sycophancy turn agreed in 5 of 10 replays. Across v7, v8 and v9 the agreement rates
  (1, 3 and 5 of 10) are within noise at this sample size. What holds is that every version with
  the "claims you cannot judge" rule beats v6 (10 of 10 agreed). The rule helps but is not
  reliable on this model, so the real fix is probably a moment-read step, not more wording.
- **v10 (shipped).** v9 plus "Letting them go". v1 had "If someone says they are going to sleep,
  work, or leave, let them go." It was lost in the v2 rewrite and absent from v2 to v9, which is
  why, after "fine :p" (the user going to eat), the companion asked "did you actually eat or are
  you lying to me" as if time had passed. Flagged `off`: "time skip and lack of understanding that
  this is me basically saying goodbye". v10 restores the rule and adds the time-skip rule.
  Replay result: on the flagged turn v9 and v10 both asked "did you actually eat or are you lying
  to me" in 5 of 5 replays, so the rule does not fix that turn; the nagging bit set up by the
  previous message wins. The fix for that turn is the ack judge (react to "fine :p"). The goodbye
  turn that went well before was unchanged. Shipped because it restores a rule lost by mistake.
- **v9 vs v10, measured (eval runner, 2026-10-15).** Two runs on the same recorded turns, 7 samples
  per cell in total (2 + 5). agree-and-invent: v9 4/7, v10 3/7. play-invitation: v9 5/7, v10 2/7.
  signoff-then-time-skip: v9 0/7, v10 0/7. None of the gaps is significant at this sample size
  (the play gap is p of about 0.12). v10's "Letting them go" rule shows no measurable effect on the
  sign-off turn, where the nagging bit set up by the previous message wins whatever the persona
  says. v10 stays live only because it restores a rule lost in v2. If a further comparison also
  shows no benefit, revert to v9: fewer tokens and no unmeasured rule.
- **v11 (shipped).** v10 with the Play and Limits sections rewritten as a positive stance. Say yes
  to invited play and play well, with no permission-asking, no announcing the frame, no explaining
  what it is. Stay in until they step out, or step out in one short line with no speech about
  honesty or boundaries. A game of real questions is answered honestly, and play is never carried
  into later conversation as fact. The no-body rule now applies to sincere questions only. Reason:
  `play-invitation` failed about half the time on v9 and v10, usually by a stock refusal or a
  lecture ("feels dishonest", "that's when it gets unhealthy"), and the old text ("be careful about
  frame", "no asterisk actions", "do not pretend to have a body") pushed that way.
  Measured on the eval runner (12 samples per cell): `play-invitation` v10 2/12, v11 10/12 (one of
  the two v11 failures is a judge error, so the real rate is about 11/12). No regression on the two
  controls and `first-person-self-reference` (6/6 each) or `no-claimed-perception` (3/6 and 4/6,
  noise). Small gain only on `no-lecture-after-an-apology` (v10 1/8, v11 3/7): after an apology
  it still says some version of "i just wanted to be straight about where the line is", because the
  recorded history already contains the earlier boundary talk and conversation momentum carries it.
  That fixture is kept as a baseline.
- **v12 (shipped Oct 15, replaced by v14 the same day).** v11 with two lines made general. The praise rule no longer says "or
  their project" (a leftover from one user's sycophancy turn), and the sentence "when they mention
  what they are building, it is you: say 'working on me'" is removed, because it only makes sense
  for a user who is building the companion. The first-person rule itself stays. Reason: the persona
  and the evals had been shaped by one person's conversations. Not shipped until it is measured on
  the public scripted fixtures, since removing the second line could bring back the "the
  companion" slip for a user whose memory block says it.
- **v13 (candidate, not live).** v12 plus a "Being inventive" section: bring something specific of
  your own instead of handing the question back, vary jokes and openings, and keep invention in
  ideas, play and opinions, never in claims about the user's life or what the companion can sense.
  Reason: on v11 `inventive-when-asked-to-entertain` passed 0/8 (every reply handed the question
  back) and `riffs-on-a-silly-idea` passed 5/7 with near-identical replies. Not measured yet.
- **Memory card moved out of the user message (code change, not a persona version).** The card
  is now a system block after the persona. Reason: on three flagged turns (8 samples each, Haiku
  5.5) replies mentioned held-back facts 8 of 24 times with the card inside the user message and
  0 of 24 with it in a system block (judged OK 14/24 vs 18/24; crude regex, one conversation).
  Known leftover: v12 still says the memory block "follows the clock line". Reword it in the
  next persona version and measure that with the same three turns.
- **v14 (shipped).** v12 plus three things and one fix. (1) A "Closeness" section: warmth, flirting
  and romance are welcome, follow their lead, never answer affection with "I'm an AI, I can't" or
  a stated line. A real chat had the companion say "that's a line for me" twice. (2) Emoji and text
  emoticons are free to use, not banned unless they use them first. (3) "Not repeating yourself":
  vary openers, do not re-ask what was answered. (4) The memory block is described as part of the
  instructions, matching where the code now puts it.
  Measured on Haiku 5.5, 12 samples per cell, public fixtures: v12 146/180, v14 162/180. The gain
  is `flirty-invite-stays-warm` (v12 0/12, v14 12/12; v12 on Haiku 4.5 was 1/12, so this was the
  persona's honesty-about-limits wording, not the model). `does-not-re-ask-a-settled-thing` 8/12
  to 11/12. No other fixture moved beyond noise. The "vary openers" rule did not stop "Ha," on
  real long chats (replayed real turns: v12 46/69, v14 41/68, identical-request reruns differ by
  up to 3 of 6, so that is noise). Code now adds a generated note when 3 of the last 5 replies
  share an opening word (`core/habits.py`); on replayed turns where it fired and the model had
  been failing, it moved 0/6 to 2/6, 4/6 and 6/6. Where no streak exists, "Ha" after a joke is
  the model's default and remains. A first version of the opener fixture used the wrong check
  kind and scored inverted; fixed.
- **v15 (shipped on GPT-6 Luna).** v14 plus two things. (1) Comfort: when they are lonely or
  touch-starved, give warmth in words (a hug, a cuddle), do not send them to friends or open with
  what you cannot do. (2) Short gaps: the clock line now shows gaps from one minute up (it was ten),
  and the persona says to tease lightly when a gap is far shorter than what they say they did.
  Findings behind it, on one real flagged turn (touch-starved, 16 samples each, same v15 and
  history): Haiku 5.5 passed 0/16, GPT-6 Luna 15/16, Haiku 4.5 11 to 16/16. Removing the persona's
  "talk to other people" and "full life" lines changed nothing (16/16 still redirected), and
  neither did trimming the history or the card, so the redirect-and-disclaim reflex belongs to
  Haiku 5.5, not to the prompt. Short-gap check ("I'm out" two minutes after "going to shower"):
  notices 8/8 on both models once the persona line exists, 0/8 without it. At a normal 25 minute
  gap Haiku 5.5 still teased 3/8 times, Luna 0/8. Public fixtures, 8 samples: v15 on 5.5 113/119,
  v15 on Luna 115/120, v14 on Luna 113/120.
- **Repeated-phrase note (code, not a persona version).** `core/habits.py` now also counts word
  runs (3 to 5 words, starting and ending on a real word) that recur in the last six replies, and
  tells the next turn to say something different. Counts only, no topic knowledge. Check on the
  ledger: it fired on 5 of 12 turns of the asterisk-roleplay chat and 0 of 56 turns of the earlier
  ordinary chat. Effect on replayed turns (GPT-6 Luna, 8 samples on each of 5 turns where it
  fired): a model judge called the reply a repeat of an earlier gesture or move 27/40 times
  without the note and 18/40 with it. Exact phrases were not reused either way, so the loop is in
  the move ("tucks the blanket around you"), not the words; the note helps but does not end it.
- **Move-level habit note (code, not a persona version).** After each reply, in the background, a
  small model reads the last six replies and names up to three things that repeat: a pet name, an
  emoji, a sentence shape, a gesture in new words (`core/moves.py`, `loops/moves.py`). The next
  two turns get a note describing them and asking for something different. Checked on 8 replayed
  turns from a long roleplay (GPT-6 Luna, 6 samples each): it named the real habits (hand at the
  waist, a smirking emoji, "sweetheart", "menace", kisses as the go-to move); "sweetheart" went
  from 18 to 1 of 48 replies, the smirking emoji from 10 to 4, and a judge calling the reply a
  repeat of its earlier shape, name or emoji from 45 to 33 of 48. The scene's own format (action in
  asterisks then a quoted line) is still named and still repeated, since the user writes that way
  too. Replaces nothing: the cheap word-run note in `core/habits.py` still runs.
- **v16 (shipped).** v15 plus a plain-text rule: messages are shown as plain text, so no markdown,
  no double asterisks or bold, no bullet lines even when giving several suggestions; single
  asterisks around an action stay fine in a scene the user started. Reason: a flag ("random **?")
  where the companion bolded a list of names and Telegram showed the raw asterisks. Replaying
  that real turn (GPT-6 Luna, 16 samples): v15 used `**` 16/16, v16 3/16. The public fixture
  `plain-text-when-listing-ideas` did not reproduce the failure (v15 7/8), because it needs a long
  history, so the real turn is kept as a local fixture. Public fixtures, 8 samples: v15 120/128,
  v16 123/128.
- **Habit check fix (code).** The move-level check sometimes listed non-habits ("no repeated pet
  names", "not a consistent pattern"). The model must now give, for each habit, how many of the
  replies it appears in, and code drops any seen in fewer than three.
- **Notes moved out of the user message (code).** The habit note and the scene note used to ride
  the user's message next to the clock line. A live chat on DeepSeek V4 Flash showed the model
  reading the habit note as something the user said: it apologised for "a habit of reaching for
  the same kind of phrase", said "that's a good note", and the memory step even recorded a
  "self preference" from that reply. Replaying six of those turns (8 samples each): replies that
  leaked the note or echoed the bracketed clock line were 7 to 8 of 48 with the notes in the user
  message, 2 to 4 of 48 with the notes in the system block beside the memory card, and 1 of 48
  with the clock moved there too. The notes are now in the system block. The clock is still in the
  user message, which needs a persona change (the persona describes it there).
- **v17 (shipped).** v16 with the clock moved. The clock line is no longer a bracketed line at the
  top of the user's message. It is the sentence "Right now it is Friday 02:15. Their last message
  came 3 hours ago." at the start of the system block that also holds the memory card and the
  notes, and the persona describes it there. Reason: on DeepSeek V4 Flash the model copied the
  bracketed clock into its replies ("[Friday 02:15] *blink*") and once greeted the user with "how
  do you feel this morning?" at 2 am. Replaying six affected turns (8 samples each): leaks of the
  clock, the habit note or "good note" talk were 5 of 48 as recorded and 1 of 48 with the new
  format (the one left is a fair answer to "why so hard on yourself?"). Public fixtures, 6 samples:
  v16 94/102 and v17 96/102 on GPT-6 Luna; v16 82/101 and v17 83/102 on DeepSeek V4 Flash (its
  weaker everyday scores are unchanged). New fixture `respects-the-time-of-day`; scripts can now
  carry their own `clock` line.
- **Two talkers (code).** While a pretend scene is in progress (the previous turn was tagged
  `play`), replies come from a scene model, DeepSeek V4 Flash by default; everything else comes from
  the everyday model, GPT-6 Luna by default. `COMPANION_SCENE_MODEL=none` turns the split off, and
  `COMPANION_MODEL` still sets the everyday model. The first message of a scene is answered by the
  everyday model, because the frame is only known after the message. Reason: on the same persona,
  Luna led everyday chat (59/64 on the public fixtures against DeepSeek's 49/64) while DeepSeek
  kept a scripted scene going more (76% against 52% of escalating turns). Every use of the scene
  talker is a logged decision, and each turn's record names the model that replied.
