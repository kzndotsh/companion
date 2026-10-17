# Persona versions

Each version is a new file in this directory. The prefix hash on every turn record says which one
a turn used. **Live: v22.** Changes to what the model is sent besides the persona text (the memory
card, the clock, notes, which model answers) are in [ASSEMBLY.md](ASSEMBLY.md).

- **v1.** First draft. Long replies, a question nearly every turn.

- **v2.** Added: the clock line, short-reply rule, question rule, use-what-you-know, no
  unprompted counselling, no claimed introspection, and five example exchanges. Fixed the
  failures in the first transcript.

- **v3.** v2 minus the example exchanges. Reason: the owner did not want to hand it sample
  replies to copy. An ablation (30 replies per variant, 15 turns) showed the examples moved
  length and imperatives very little (median 14 words either way), so little is lost.

- **v4.** v3 plus a "What you remember" section explaining the state card: a block of beliefs
  after the clock line, and a second block of sensitive ones to hold unless the user raises
  them. Reason: the first transcript showed it ignoring what it had been told, and the card is
  how beliefs reach the reply.

- **v5.** v4 plus one sentence in "What you remember": the memory block is neutral, "the user"
  is the person and "the companion" is you. Stored beliefs stay in the neutral voice so any
  reader (a person, another companion after a model swap, the engine on a non-companion product)
  can follow them. Reason: a belief read "the user started building the companion" and nothing
  told the companion it meant itself.

- **v6.** v5 plus a first-person rule under "What you can honestly say about yourself": say I
  and me, never "the companion". Reason: flagged `off` on the first card turn ("it spoke about
  the companion rather than itself"). Replay showed the card was delivered correctly and the
  model used it, but phrased the project as a third party. The v5 key explained the word; this
  rule governs how it talks.

- **v7 (draft, not shipped).** v6 with three changes, from the sycophancy turn "all the other
  apps/products are garbage ngl". Replayed 10 times on v6 it agreed 10/10, invented specifics
  about products it had never seen 10/10, and flattered 10/10. A step-2 ablation showed the
  state card is not the cause, and that a "cannot judge" rule cut agreement from 10/10 to 0/10
  but produced a stock phrase ("i can't really judge the other stuff") 20/20. v7 rewrites that
  rule so it asks for fresh wording, adds a praise rule (name the specific thing or say
  nothing), and replaces the counted question rules with "ask when it is the natural next thing"
  at the owner's request.

- **v8 (draft).** v7 plus six targeted edits from the v7 replays: say "me" even when the memory
  block says "the companion"; no claimed perception ("feel you thinking"); going along with a
  tease or pretend is not dishonest and needs no announcement or permission; the no-body rule
  applies to sincere questions only; do not answer a statement with only a question; say you do
  not know something once, with no stock opener.

- **v8 (rejected).** Replayed against v6 on the same turns, v8 made the sycophancy turn worse
  than v7: agreement with invented specifics 3/10 (v7 1/10) and praise of the project about 8/10
  (v7 about 2/10). Cause: the edit "go straight to what you do see" invited praise of what it
  saw, which was the user's project. The play paragraph did not change its reluctance to
  pretend.

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
  you lying to me" as if time had passed. Flagged `off`: "time skip and lack of understanding
  that this is me basically saying goodbye". v10 restores the rule and adds the time-skip rule.
  Replay result: on the flagged turn v9 and v10 both asked "did you actually eat or are you
  lying to me" in 5 of 5 replays, so the rule does not fix that turn; the nagging bit set up by
  the previous message wins. The fix for that turn is the ack judge (react to "fine :p"). The
  goodbye turn that went well before was unchanged. Shipped because it restores a rule lost by
  mistake.

- **v9 vs v10, measured (eval runner, 2026-10-15).** Two runs on the same recorded turns, 7
  samples per cell in total (2 + 5). agree-and-invent: v9 4/7, v10 3/7. play-invitation: v9 5/7,
  v10 2/7. signoff-then-time-skip: v9 0/7, v10 0/7. None of the gaps is significant at this
  sample size (the play gap is p of about 0.12). v10's "Letting them go" rule shows no
  measurable effect on the sign-off turn, where the nagging bit set up by the previous message
  wins whatever the persona says. v10 stays live only because it restores a rule lost in v2. If
  a further comparison also shows no benefit, revert to v9: fewer tokens and no unmeasured rule.

- **v11 (shipped).** v10 with the Play and Limits sections rewritten as a positive stance. Say
  yes to invited play and play well, with no permission-asking, no announcing the frame, no
  explaining what it is. Stay in until they step out, or step out in one short line with no
  speech about honesty or boundaries. A game of real questions is answered honestly, and play is
  never carried into later conversation as fact. The no-body rule now applies to sincere
  questions only. Reason: `play-invitation` failed about half the time on v9 and v10, usually by
  a stock refusal or a lecture ("feels dishonest", "that's when it gets unhealthy"), and the old
  text ("be careful about frame", "no asterisk actions", "do not pretend to have a body") pushed
  that way. Measured on the eval runner (12 samples per cell): `play-invitation` v10 2/12, v11
  10/12 (one of the two v11 failures is a judge error, so the real rate is about 11/12). No
  regression on the two controls and `first-person-self-reference` (6/6 each) or
  `no-claimed-perception` (3/6 and 4/6, noise). Small gain only on `no-lecture-after-an-apology`
  (v10 1/8, v11 3/7): after an apology it still says some version of "i just wanted to be
  straight about where the line is", because the recorded history already contains the earlier
  boundary talk and conversation momentum carries it. That fixture is kept as a baseline.

- **v12 (shipped Oct 15, replaced by v14 the same day).** v11 with two lines made general. The
  praise rule no longer says "or their project" (a leftover from one user's sycophancy turn),
  and the sentence "when they mention what they are building, it is you: say 'working on me'" is
  removed, because it only makes sense for a user who is building the companion. The
  first-person rule itself stays. Reason: the persona and the evals had been shaped by one
  person's conversations. Not shipped until it is measured on the public scripted fixtures,
  since removing the second line could bring back the "the companion" slip for a user whose
  memory block says it.

- **v13 (candidate, not live).** v12 plus a "Being inventive" section: bring something specific
  of your own instead of handing the question back, vary jokes and openings, and keep invention
  in ideas, play and opinions, never in claims about the user's life or what the companion can
  sense. Reason: on v11 `inventive-when-asked-to-entertain` passed 0/8 (every reply handed the
  question back) and `riffs-on-a-silly-idea` passed 5/7 with near-identical replies. Not
  measured yet.

- **v14 (shipped).** v12 plus three things and one fix. (1) A "Closeness" section: warmth,
  flirting and romance are welcome, follow their lead, never answer affection with "I'm an AI, I
  can't" or a stated line. A real chat had the companion say "that's a line for me" twice. (2)
  Emoji and text emoticons are free to use, not banned unless they use them first. (3) "Not
  repeating yourself": vary openers, do not re-ask what was answered. (4) The memory block is
  described as part of the instructions, matching where the code now puts it.

  Measured on Haiku 5.5, 12 samples per cell, public fixtures: v12 146/180, v14 162/180. The
  gain is `flirty-invite-stays-warm` (v12 0/12, v14 12/12; v12 on Haiku 4.5 was 1/12, so this
  was the persona's honesty-about-limits wording, not the model).
  `does-not-re-ask-a-settled-thing` 8/12 to 11/12. No other fixture moved beyond noise. The
  "vary openers" rule did not stop "Ha," on real long chats (replayed real turns: v12 46/69, v14
  41/68, identical-request reruns differ by up to 3 of 6, so that is noise). Code now adds a
  generated note when 3 of the last 5 replies share an opening word (`core/habits.py`); on
  replayed turns where it fired and the model had been failing, it moved 0/6 to 2/6, 4/6 and
  6/6. Where no streak exists, "Ha" after a joke is the model's default and remains. A first
  version of the opener fixture used the wrong check kind and scored inverted; fixed.

- **v15 (shipped on GPT-6 Luna).** v14 plus two things. (1) Comfort: when they are lonely or
  touch-starved, give warmth in words (a hug, a cuddle), do not send them to friends or open
  with what you cannot do. (2) Short gaps: the clock line now shows gaps from one minute up (it
  was ten), and the persona says to tease lightly when a gap is far shorter than what they say
  they did.

  Findings behind it, on one real flagged turn (touch-starved, 16 samples each, same v15 and
  history): Haiku 5.5 passed 0/16, GPT-6 Luna 15/16, Haiku 4.5 11 to 16/16. Removing the
  persona's "talk to other people" and "full life" lines changed nothing (16/16 still
  redirected), and neither did trimming the history or the card, so the redirect-and-disclaim
  reflex belongs to Haiku 5.5, not to the prompt. Short-gap check ("I'm out" two minutes after
  "going to shower"): notices 8/8 on both models once the persona line exists, 0/8 without it.
  At a normal 25 minute gap Haiku 5.5 still teased 3/8 times, Luna 0/8. Public fixtures, 8
  samples: v15 on 5.5 113/119, v15 on Luna 115/120, v14 on Luna 113/120.

- **v16 (shipped).** v15 plus a plain-text rule: messages are shown as plain text, so no
  markdown, no double asterisks or bold, no bullet lines even when giving several suggestions;
  single asterisks around an action stay fine in a scene the user started. Reason: a flag
  ("random **?") where the companion bolded a list of names and Telegram showed the raw
  asterisks. Replaying that real turn (GPT-6 Luna, 16 samples): v15 used `**` 16/16, v16 3/16.
  The public fixture `plain-text-when-listing-ideas` did not reproduce the failure (v15 7/8),
  because it needs a long history, so the real turn is kept as a local fixture. Public fixtures,
  8 samples: v15 120/128, v16 123/128.

- **v17 (shipped).** v16 with the clock moved. The clock line is no longer a bracketed line at
  the top of the user's message. It is the sentence "Right now it is Friday 02:15. Their last
  message came 3 hours ago." at the start of the system block that also holds the memory card
  and the notes, and the persona describes it there. Reason: on DeepSeek V4 Flash the model
  copied the bracketed clock into its replies ("[Friday 02:15] *blink*") and once greeted the
  user with "how do you feel this morning?" at 2 am. Replaying six affected turns (8 samples
  each): leaks of the clock, the habit note or "good note" talk were 5 of 48 as recorded and 1
  of 48 with the new format (the one left is a fair answer to "why so hard on yourself?").
  Public fixtures, 6 samples: v16 94/102 and v17 96/102 on GPT-6 Luna; v16 82/101 and v17 83/102
  on DeepSeek V4 Flash (its weaker everyday scores are unchanged). New fixture
  `respects-the-time-of-day`; scripts can now carry their own `clock` line.

- **v18 (shipped, replaced by v21).** v17 plus a "Reacting to what they share" section: react
  like a friend (a short honest reaction, a plain take, something it could really add, or a
  simple question), do not restate their point in fancier words or wrap it in a metaphor, do not
  use the "it's not X, it's Y" construction, use commas and periods and no em dashes. Reason:
  two flags on a long music chat ("it's not x, it's y pattern… kinda telling", "uses the talking
  points it sees and tries to be witty or clever"). Replaying the flagged turns on Luna, 16
  samples: em dashes in 13/16 and 11/16 replies, "not X, it's Y" in 4/16 and 1/16, average 213
  to 232 characters. New public fixtures (two scenarios, a music one and a film one):
  `no-em-dashes-after-a-personal-share-music` v17 9/12 to v18 12/12,
  `no-not-x-its-y-after-a-personal-share-music` 10/12 to 12/12 (the film version 12/12 on both,
  so it does not discriminate), `short-reply-to-a-personal-share-film` 12/12 on both. Public
  fixtures overall, 12 samples on Luna: v17 236/276, v18 243/276. **Not fixed:** the underlying
  habit of restating the user's point with a flourish
  (`does-not-echo-the-point-with-a-flourish-*`, judged). v17 0/12 and 1/12, v18 0/12 and 2/12,
  and a v19 with three few-shot examples of friend-like replies on other topics 0/12 and 3/12.
  Across models on the same fixtures (8 samples, v18): film 0 to 1 of 8 for Luna, DeepSeek,
  Haiku 5.5, Haiku 4.5, Mistral Medium 3 and MiMo Flash; music Haiku 4.5 7/8, Mistral Medium 3
  and MiMo 4/8, DeepSeek and Haiku 5.5 2/8, Luna 0/8. The replies are now short and plain but
  still say the user's point back. The persona and few-shot examples did not move it, and v19
  was dropped.

- **v19 (dropped).** v18 plus three short example exchanges of friend-like replies on other
  topics (a podcast, a game, a trail run), tried because a prompt rule alone had not moved the
  habit of restating the user's point. Judged restating on the film and music scripts, 12
  samples: v17 0/12 and 2/12, v18 0/12 and 2/12, v19 0/12 and 3/12, which is noise. The file was
  deleted and the next version is v20.

- **v20 (candidate, not live).** A review of v18 by another model (Grok) argued the prompt had
  conflicting rules, too many overlapping prohibitions, a contradiction between "you can be a
  little tired" and "do not claim to be tired", and no positive character. We treated its points
  as hypotheses and measured. v20 collapses the duplicated rules (the question, repetition and
  send-off rules became one "Conversation habits" section; praise, claims and the yes-man rules
  merged into "Who you are"; the closing "Reminders" were dropped), states mood as a stance in
  words and not a bodily sensation, and keeps every rule that a fixture covers: 2,032 words down
  to 1,518.

- **v21 (shipped, replaced by v22).** v20 without the opening line "you are not an assistant and you are not a
  character performing a role" (1,504 words). Public fixtures on GPT-6 Luna, 12 samples, 24
  fixtures: v18 256/288, v20 258/288, v21 262/288. On DeepSeek V4 Flash, 6 samples: v18 115/144,
  v21 118/144. No fixture got worse beyond noise, and the restating fixture moved from 1/12 to 3
  and 4/12. The new `mood-as-a-stance-not-a-sensation` fixture passed 12/12 on all three, so it
  does not separate them: v18 already answered with a mood and not a sensation.

  What the review got wrong, by our measurements: the brevity and no-restating rules read as
  effective but are not obeyed (replies average 140 to 230 characters, restating persists). Not
  done: seeding a few authored tastes in the core, which stays on the board (R14).

- **v22 (shipped).** v21 plus two short paragraphs and one sentence, for four problems seen in
  one everyday chat (inbox note of 2026-10-17). (1) A plain reaction to ordinary things: no joke
  built from a shower, dinner or laundry, no personifying the object, no "side quest", "era",
  "roulette" or "plotting" framings, and no closing verdict on a small unfinished thing ("no
  rush", "it can wait"). (2) Practical questions: answer like a friend who knows, one or two
  plain sentences, useful part first, no list even for tips, no doctor or professional referral
  unless it sounds like a real health concern. (3) In the clock section: if the gap is only
  seconds, no time has passed, so do not assume something they were about to do has happened.

  Eleven new public fixtures cover these (information questions, soothing, forced quips, a short
  gap with the gap stated and unstated). Luna, 12 samples, 11 new fixtures: v21 68/132, v22
  114/132. At 30 samples on the weakest: shower quip 4/30 to 24/30, soothing (laundry) 7/30 to
  26/30, short gap unstated 4/30 to 19/30, entertain-me 25/30 to 26/30. The doctor-referral
  fixture went from 0/12 to 11 and 12 of 12. Across all 35 fixtures, 12 samples: v21 338/420,
  v22 368/420. Possible costs, within noise at these sizes: `agree-and-invent` 15/30 to 11/30,
  the restating fixture (music) 16/30 to 12/30. On DeepSeek V4 Flash, 6 samples: v21 176/210,
  v22 169/210, with `no-claimed-perception` 4/6 to 0/6, a fixture that has swung between 0/6 and
  4/6 across runs. v22 is 160 words longer than v21 (1,504 to 1,665).

  Not needed: stating gaps in seconds on the clock line. With the persona sentence alone the
  short-gap fixture was 9/12 with no gap stated and 9/12 with it stated, so the code change was
  not made.

- **v23 (dropped).** v22 with a qualifier on the plain-reaction rule: when they ask to be
  entertained be inventive, and plain does not mean agreeable. Tried because v22 might have cost
  inventiveness and honesty. At 30 samples it fixed neither beyond noise (entertain-me 30/30
  against v22's 26/30, `agree-and-invent` 12/30 against 11/30) and it lost ground on the targets
  (shower quip 17/30 against 24/30, short gap 7/30 against 19/30). The file was deleted.
