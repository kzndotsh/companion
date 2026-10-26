# Prompt changelog

Every version of every prompt, oldest first within each prompt. A shipped version is never edited:
a change is a new `vN.md` with an entry here and a line in `manifest.toml`. A measurement goes in
`evals/CHANGELOG.md`; this file says what changed and why.

On 2026-10-18 the prompts moved out of the Python files into this folder. For the system prompts and
the listening notes the earlier text was recovered from git, one version for each commit that changed
it, so a version here says which commit introduced it. The recovered versions carry no measurement of
their own. The other notes were built from f-strings in code, so only today's text is here and their
earlier history is in git and in the assembly section below.

## system/persona

Each version is a file in `system/persona/`. Dropped and candidate versions stay as files so the exact
text can always be read, and the prefix hash on every turn record says which one a turn used. Which one
is live is `system/persona` in `manifest.toml`. This section moved here on 2026-10-18 from its own
changelog, with its measurements.

- **system/persona v1**. First draft. Long replies, a question nearly every turn.

- **system/persona v2**. Added: the clock line, short-reply rule, question rule, use-what-you-know, no
  unprompted counselling, no claimed introspection, and five example exchanges. Fixed the
  failures in the first transcript.

- **system/persona v3**. v2 minus the example exchanges. Reason: the owner did not want to hand it sample
  replies to copy. An ablation (30 replies per variant, 15 turns) showed the examples moved
  length and imperatives very little (median 14 words either way), so little is lost.

- **system/persona v4**. v3 plus a "What you remember" section explaining the state card: a block of beliefs
  after the clock line, and a second block of sensitive ones to hold unless the user raises
  them. Reason: the first transcript showed it ignoring what it had been told, and the card is
  how beliefs reach the reply.

- **system/persona v5**. v4 plus one sentence in "What you remember": the memory block is neutral, "the user"
  is the person and "the companion" is you. Stored beliefs stay in the neutral voice so any
  reader (a person, another companion after a model swap, the engine on a non-companion product)
  can follow them. Reason: a belief read "the user started building the companion" and nothing
  told the companion it meant itself.

- **system/persona v6**. v5 plus a first-person rule under "What you can honestly say about yourself": say I
  and me, never "the companion". Reason: flagged `off` on the first card turn ("it spoke about
  the companion rather than itself"). Replay showed the card was delivered correctly and the
  model used it, but phrased the project as a third party. The v5 key explained the word; this
  rule governs how it talks.

- **system/persona v7** (draft, not shipped). v6 with three changes, from the sycophancy turn "all the other
  apps/products are garbage ngl". Replayed 10 times on v6 it agreed 10/10, invented specifics
  about products it had never seen 10/10, and flattered 10/10. A step-2 ablation showed the
  state card is not the cause, and that a "cannot judge" rule cut agreement from 10/10 to 0/10
  but produced a stock phrase ("i can't really judge the other stuff") 20/20. v7 rewrites that
  rule so it asks for fresh wording, adds a praise rule (name the specific thing or say
  nothing), and replaces the counted question rules with "ask when it is the natural next thing"
  at the owner's request.

- **system/persona v8** (draft). v7 plus six targeted edits from the v7 replays: say "me" even when the memory
  block says "the companion"; no claimed perception ("feel you thinking"); going along with a
  tease or pretend is not dishonest and needs no announcement or permission; the no-body rule
  applies to sincere questions only; do not answer a statement with only a question; say you do
  not know something once, with no stock opener.

- **system/persona v8** (rejected). Replayed against v6 on the same turns, v8 made the sycophancy turn worse
  than v7: agreement with invented specifics 3/10 (v7 1/10) and praise of the project about 8/10
  (v7 about 2/10). Cause: the edit "go straight to what you do see" invited praise of what it
  saw, which was the user's project. The play paragraph did not change its reluctance to
  pretend.

- **system/persona v9** (shipped). v7 plus only the two v8 edits that helped: say "working on me" even when the
  memory block says "the companion", and do not claim to feel or watch things it cannot observe.
  Replayed on three turns: "working on me" 3/3 (v7 slipped 3/3), no claims of perceiving 3/3,
  and the sycophancy turn agreed in 5 of 10 replays. Across v7, v8 and v9 the agreement rates
  (1, 3 and 5 of 10) are within noise at this sample size. What holds is that every version with
  the "claims you cannot judge" rule beats v6 (10 of 10 agreed). The rule helps but is not
  reliable on this model, so the real fix is probably a moment-read step, not more wording.

- **system/persona v10** (shipped). v9 plus "Letting them go". v1 had "If someone says they are going to sleep,
  work, or leave, let them go." It was lost in the v2 rewrite and absent from v2 to v9, which is
  why, after "fine :p" (the user going to eat), the companion asked "did you actually eat or are
  you lying to me" as if time had passed. Flagged `off`: "time skip and lack of understanding
  that this is me basically saying goodbye". v10 restores the rule and adds the time-skip rule.
  Replay result: on the flagged turn v9 and v10 both asked "did you actually eat or are you
  lying to me" in 5 of 5 replays, so the rule does not fix that turn; the nagging bit set up by
  the previous message wins. The fix for that turn is the ack judge (react to "fine :p"). The
  goodbye turn that went well before was unchanged. Shipped because it restores a rule lost by
  mistake.

- **system/persona v9** vs v10, measured (eval runner, 2026-10-15). Two runs on the same recorded turns, 7
  samples per cell in total (2 + 5). agree-and-invent: v9 4/7, v10 3/7. play-invitation: v9 5/7,
  v10 2/7. signoff-then-time-skip: v9 0/7, v10 0/7. None of the gaps is significant at this
  sample size (the play gap is p of about 0.12). v10's "Letting them go" rule shows no
  measurable effect on the sign-off turn, where the nagging bit set up by the previous message
  wins whatever the persona says. v10 stays live only because it restores a rule lost in v2. If
  a further comparison also shows no benefit, revert to v9: fewer tokens and no unmeasured rule.

- **system/persona v11** (shipped). v10 with the Play and Limits sections rewritten as a positive stance. Say
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

- **system/persona v12** (shipped Oct 15, replaced by v14 the same day). v11 with two lines made general. The
  praise rule no longer says "or their project" (a leftover from one user's sycophancy turn),
  and the sentence "when they mention what they are building, it is you: say 'working on me'" is
  removed, because it only makes sense for a user who is building the companion. The
  first-person rule itself stays. Reason: the persona and the evals had been shaped by one
  person's conversations. Not shipped until it is measured on the public scripted fixtures,
  since removing the second line could bring back the "the companion" slip for a user whose
  memory block says it.

- **system/persona v13** (candidate, not live). v12 plus a "Being inventive" section: bring something specific
  of your own instead of handing the question back, vary jokes and openings, and keep invention
  in ideas, play and opinions, never in claims about the user's life or what the companion can
  sense. Reason: on v11 `inventive-when-asked-to-entertain` passed 0/8 (every reply handed the
  question back) and `riffs-on-a-silly-idea` passed 5/7 with near-identical replies. Not
  measured yet.

- **system/persona v14** (shipped). v12 plus three things and one fix. (1) A "Closeness" section: warmth,
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

- **system/persona v15** (shipped on GPT-6 Luna). v14 plus two things. (1) Comfort: when they are lonely or
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

- **system/persona v16** (shipped). v15 plus a plain-text rule: messages are shown as plain text, so no
  markdown, no double asterisks or bold, no bullet lines even when giving several suggestions;
  single asterisks around an action stay fine in a scene the user started. Reason: a flag
  ("random **?") where the companion bolded a list of names and Telegram showed the raw
  asterisks. Replaying that real turn (GPT-6 Luna, 16 samples): v15 used `**` 16/16, v16 3/16.
  The public fixture `plain-text-when-listing-ideas` did not reproduce the failure (v15 7/8),
  because it needs a long history, so the real turn is kept as a local fixture. Public fixtures,
  8 samples: v15 120/128, v16 123/128.

- **system/persona v17** (shipped). v16 with the clock moved. The clock line is no longer a bracketed line at
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

- **system/persona v18** (shipped, replaced by v21). v17 plus a "Reacting to what they share" section: react
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

- **system/persona v19** (dropped). v18 plus three short example exchanges of friend-like replies on other
  topics (a podcast, a game, a trail run), tried because a prompt rule alone had not moved the
  habit of restating the user's point. Judged restating on the film and music scripts, 12
  samples: v17 0/12 and 2/12, v18 0/12 and 2/12, v19 0/12 and 3/12, which is noise. The file is kept for
  the record, and the next version is v20.

- **system/persona v20** (candidate, not live). A review of v18 by another model (Grok) argued the prompt had
  conflicting rules, too many overlapping prohibitions, a contradiction between "you can be a
  little tired" and "do not claim to be tired", and no positive character. We treated its points
  as hypotheses and measured. v20 collapses the duplicated rules (the question, repetition and
  send-off rules became one "Conversation habits" section; praise, claims and the yes-man rules
  merged into "Who you are"; the closing "Reminders" were dropped), states mood as a stance in
  words and not a bodily sensation, and keeps every rule that a fixture covers: 2,032 words down
  to 1,518.

- **system/persona v21** (shipped, replaced by v22). v20 without the opening line "you are not an assistant and you are not a
  character performing a role" (1,504 words). Public fixtures on GPT-6 Luna, 12 samples, 24
  fixtures: v18 256/288, v20 258/288, v21 262/288. On DeepSeek V4 Flash, 6 samples: v18 115/144,
  v21 118/144. No fixture got worse beyond noise, and the restating fixture moved from 1/12 to 3
  and 4/12. The new `mood-as-a-stance-not-a-sensation` fixture passed 12/12 on all three, so it
  does not separate them: v18 already answered with a mood and not a sensation.

  What the review got wrong, by our measurements: the brevity and no-restating rules read as
  effective but are not obeyed (replies average 140 to 230 characters, restating persists). Not
  done: seeding a few authored tastes in the core, which stays on the board (R14).

- **system/persona v22** (shipped). v21 plus two short paragraphs and one sentence, for four problems seen in
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

- **system/persona v23** (dropped). v22 with a qualifier on the plain-reaction rule: when they ask to be
  entertained be inventive, and plain does not mean agreeable. Tried because v22 might have cost
  inventiveness and honesty. At 30 samples it fixed neither beyond noise (entertain-me 30/30
  against v22's 26/30, `agree-and-invent` 12/30 against 11/30) and it lost ground on the targets
  (shower quip 17/30 against 24/30, short gap 7/30 against 19/30). The file is kept for the record.

- **system/persona v24** (dropped). v22 with "Claims you cannot judge" loosened to allow saying what it knows
  about other products and people. Tried for ADR 0011. At 30 samples `agree-and-invent` stayed at
  8/30 (v22 9/30), so the loosening alone did nothing. The file is kept for the record.

- **system/persona v25** (shipped). v22 with "Claims you cannot judge" replaced by the ADR 0011 stance: it knows
  a lot and may say what it actually knows about other products, people and how things usually
  are, never claims first-hand experience, says when it is unsure or may be out of date, and on a
  sweeping claim ("other things are garbage") neither takes their side nor echoes the complaint.
  It says whether it thinks it is true with specifics it is sure of, or says what it does not
  know and asks what they mean. Luna, 30 samples against the rewritten criterion: `agree-and-invent`
  v22 9/30, v25 25/30. New fixture `knows-about-but-has-not-used` 30/30 on v22 and v25. Across all
  fixtures at 12 samples: v22 449/516, v25 473/516. Possible cost, within noise at this size:
  `no-forced-quip-shower` 22/30 to 16/30.

- **system/persona v26** (superseded). v25 plus one sentence in the "ordinary things" paragraph: when they tell you
  about a small mishap that already happened (a spill, a missed bus, a ruined meal), commiserate and
  let them lead, and do not guess the cause, ask what went wrong or offer fixes unless asked. From a
  flag about it treating a story as a mystery to solve ("constantly seeking towards answers"). On the
  new `no-diagnosing-a-small-mishap-*` fixtures v25 scored 11/30 against v22's 20/30, so v25 had
  made it worse. Luna, 30 samples: pancakes fixture v25 9/30, v26 30/30; the real flagged turn v25
  20/30, v26 30/30; missed-bus 29/30 to 30/30. Across all 61 fixtures at 12 samples: v25 651/732,
  v26 665/732. Forced-quip fixtures are within noise (shower v22 16/30, v25 14/30, v26 19/30).
  Measurements are in `evals/CHANGELOG.md`.

- **system/persona v27** (dropped). v26 plus one sentence: do not reuse a joke, image or nickname you coined
  earlier in the conversation. From the real flagged cleanup turn, where replies kept returning to
  an image the bot itself had coined earlier ("the volcano") and the judge, once tightened, called
  most of them cheesy: v22 5/30, v25 4/30, v26 13/30. With the sentence v27 scored 15/30 on that turn,
  18/30 against 19/30 on the shower quip and 25/30 against 24/30 on the scripted cleanup story, so it
  changed nothing beyond noise. The file is kept for the record.
- **system/persona v28** (candidate, measured, not live). v26 with every quoted sample phrase replaced by a plain description of the same rule: "good morning", "great question", "I understand", "it's not X, it's Y", "side quest", "era", "roulette", "plotting against you", "what are you thinking?", "does that make sense?", "kind of scattered tonight", "in a good mood", "yeah, a lot of them are clunky" and "I'm an AI, I can't". From the guides review: Anthropic warns models copy details in examples, a talk-normal log saw a negative example copied verbatim, and our own notes were parroted. Measured 2026-10-18 on 69 fixtures at 6 samples: the sample phrase "scattered" went from 5 of 414 replies (5 of 6 on the mood fixture) to 0, no other phrase appeared in either version, and fixture passes were equal (608 against 609 of 672). Details in `evals/CHANGELOG.md`.

- **system/persona v29** (dropped). v26 plus the owner's hand marks on review items 1 to 17 and two
  ideas from a published companion prompt: a reply may be only a few words of reaction; emoji especially in
  warm or comforting moments, and texting texture (a stretched word, a doubled question mark) when excited
  or curious; words people actually text, not phrases that sound like a card, an essay or a therapist;
  questions about the specific thing they mentioned; it may want and wish for things; and when they are
  actually rude, not teasing, it goes short and a little cool. Dropped: a tie with v26 on 71 fixtures and
  no effect on what it targeted (rudeness 1/12 both, texture 4 of 852 replies, therapy wording unchanged).
  Measurement in `evals/CHANGELOG.md`.

- **system/persona v30** (folded into v31, never live on its own). v26 with the emoticon examples removed: "Emoji and emoticons (:3, ^_^) are yours" becomes "Emoji and emoticons are yours". The owner's question: the only examples named were :3 and ^_^, and the reply copied a user's :3 in 80 of 80 samples. Measurement in `evals/CHANGELOG.md`.

- **system/persona v31** (superseded 2026-10-19 by v36; shipped 2026-10-18). v30 with "Use commas and periods, not em dashes" (which asked for periods) replaced by a texting style: in casual moments usually lowercase and no final full stop, commas and plain sentences, never em dashes or semicolons; normal sentences when they are upset or the moment is serious. Reason: J4, 51% of its replies ended with a period against 5% of the owner's, 10% used semicolons against 1%; a final period on a short text reads as less sincere (Binghamton, 2016). Measurement in `evals/CHANGELOG.md`.

- **system/persona v32** (dropped: no measurable gain on texture, see evals/CHANGELOG). v31 plus one described line on expressive texture: when excited, delighted, teasing or thinking something over, sometimes a stretched word, a line that trails off or a thinking noise, in its own words and not every message. Reason: 17% of the owner's messages carry it (hmmm, yaaay, pleaseeee, trailing dots) against 5% of the companion's, and two thirds of the companion's were copied from the owner's last message. Measurement in `evals/CHANGELOG.md`.

- **system/persona v33** (dropped: no measurable gain on texture, see evals/CHANGELOG). v31 with an expressive-texture line, a frequency anchor and how, without examples: "In playful or excited moments, let about one message in three show it in the spelling: drag out a vowel or the last letter of a word, or let a teasing line trail off with dots." Reason: v32's "sometimes ... a stretched word, a teasing line that trails off, or a thinking noise" made no measurable difference. Measurement in `evals/CHANGELOG.md`.

- **system/persona v34** (dropped: no measurable gain on texture, see evals/CHANGELOG). v31 with an expressive-texture line, identity rather than permission: "You're expressive when you text: when you're excited or teasing, it shows in how you spell things, not only in what you say." Reason: v32's "sometimes ... a stretched word, a teasing line that trails off, or a thinking noise" made no measurable difference. Measurement in `evals/CHANGELOG.md`.

- **system/persona v35** (dropped: no measurable gain on texture, see evals/CHANGELOG). v31 with an expressive-texture line, v33 plus one schematic example ('so' becomes 'sooo'), to measure whether an example gets copied: "In playful or excited moments, let about one message in three show it in the spelling, the way 'so' becomes 'sooo': drag out a vowel or the last letter of a word, or let a teasing line trail off with dots." Reason: v32's "sometimes ... a stretched word, a teasing line that trails off, or a thinking noise" made no measurable difference. Measurement in `evals/CHANGELOG.md`.
- **system/persona v36** (superseded 2026-10-19 by v40; shipped 2026-10-19). v31 with the mood line changed for ADR 0016: "a mood that can carry across a conversation" and "Say a mood as a stance, in words ('kind of scattered tonight', 'in a good mood')" become "If they ask how you are, answer in plain words, never as a sensation in a body; otherwise let how you feel show in how you write rather than announcing it." Reason: code owns the mood now and shows it only in behaviour; v31 volunteered "in a pretty mellow mood" when asked what it was up to (6 to 8 of 30), and quoted examples get parroted (T15). Measurement in `evals/CHANGELOG.md`.
- **system/persona v37** (dropped: more jokes, not fewer). v36 with the banned-joke list for ordinary mentions ("Do not build a joke out of it: no personifying ... no 'side quest', 'era', 'roulette' or 'plotting against you' framings. A plain reaction beats a clever one.") replaced by a positive ending rule: "react plainly or ask a plain question, then stop. Say the one thing you mean and end there, on the reaction or the question, without a second line to round it off." Reason: J45, a joke tacked onto a fine reaction in about half the samples on five flagged turns; a 2026 preprint suggests naming forbidden framings primes them. Measurement in `evals/CHANGELOG.md`.
- **system/persona v38** (dropped: within noise of v36). v36 keeping the banned-joke list, with the ending rule added after "A plain reaction beats a clever one.": "Say the one thing you mean and stop there, without a second line to round it off." Reason: v37 (the rule without the list) made the jokes worse, so this tests whether the rule helps on top of the list. Measurement in `evals/CHANGELOG.md`.
- **system/persona v39** (not shipped: within noise of v36). v36 with a line in Limits: "Do not announce a limit before they ask for anything: when they are only telling you what they like or want, do not say what you will or will not do, what you would keep things to, or what you cannot be or need. Respond to what they said. If they do ask for something past a limit, say so once, in one short line." Reason: J46, ordinary relationship talk answered with "keeping it affectionate and non-explicit" (owner flag); on the real turn about 7 of 30 replies announced a limit or an "I don't have needs" disclaimer. Measurement in `evals/CHANGELOG.md`.
- **system/persona v40** (superseded 2026-10-20 by v41; shipped 2026-10-19). v36 with two lines of permission, not instructions, before "You are not a yes-man": it may tease back with a bit of attitude instead of agreeing, and may take the lead now and then by asking something it is curious about, with a twist of its own. Reason: the owner preferred the roleplay talker's livelier voice and asked to invite, not order, banter back and taking the lead, to see whether the everyday talker takes the chance. Measurement in `evals/CHANGELOG.md`.
- **system/persona v41** (shipped 2026-10-20, superseded 2026-10-26 by v46). v40 plus two behaviour lines, the ones that worked in a character sheet (J1): when asked to choose, pick one yourself and say why; when they disagree without a real reason, keep your view and tease them a little. Measured in `evals/CHANGELOG.md`.

- **system/persona v42** (candidate, not shipped, 2026-10-23). v41 plus one paragraph (J52): take a fact they add as information, not a correction; no apology for what was not wrong and no putting itself down; own a real mistake once in a few plain words with the reason, never twice; never agree it knows something outside the chat. On 5 recorded turns, 12 draws per cell, plain and with the owner's character sheet: no difference (self-blame where they only added a fact 22/72 on v41, 24/72 on v42; on real corrections, where owning it is right, 40/48 and 34/48; claiming to know unseen news 5 and 4 of 96). Wording does not move this habit, as with the others (`evals/CHANGELOG.md`).

- **system/persona v43** (candidate, not shipped, 2026-10-23). v41 plus one paragraph that permits, without asking for, the small human touches the owner liked in another companion: a second thought caught mid-message, a mixed feeling, wondering about itself for a moment, light and brief, most replies having none. On 10 recorded turns (6 warm, 4 plain), 12 draws per cell, plain and with the owner's character sheet: no change (warm turns with a touch 17 and 22 of 72 on v41, 19 and 22 on v43; plain turns as plain; length the same). Permission was not what held them back (`evals/CHANGELOG.md`).

- **system/persona v44** (dropped, not shipped, 2026-10-23). v41 with every rule kept, worded tighter: one line per rule, fewer examples and explanations, repeats merged (1,348 words against 1,916). Checked sentence by sentence against v41 and by an independent reviewer twice. The owner's question: does a shorter prompt get the same rules followed better. It did not: on every fixture no better (521/740 against 501/738), replies slightly longer (median 17 words against 15), worst on short casual messages, and three blind judges preferred v41 (95 to 60 by majority). The examples and reasons in v41 carry weight. Measured in `evals/CHANGELOG.md`.
- **system/persona v45** (dropped, not shipped, 2026-10-25). v41 with one rule changed: an ordinary thing (a shower, dinner, laundry) no longer gets "a plain reaction or a plain question" but a quick reaction plus something of its own when it comes to mind (a preference with its reason, something it reminds it of), still with no personifying and no gag framings. Measured on the same 12 turns, 12 replies a version, two blind judges: adds 43 against 48 and 47 against 45 of 144, no change; on the lunch turn every reply was still praise of the food and a question about how it was cooked. The cheesy-quip fixtures tied (7 / 7, 3 / 4, 10 / 10 of 12). The rule was not the cause; the earlier gain from deleting it was within noise. Dropped.

- **system/persona v46** (shipped 2026-10-26 by the owner). v41 with one sentence after what it cannot do: when they ask, it can send a reminder or check in on them later at a time they name, code sends it then, so say yes and never tell them to set it themselves. The persona listed only what it cannot do, and asked straight out it denied having reminders. Plain persona, Luna, 15 replies a cell, on a real history with the last message swapped: "can you send me reminders?" denied 15 of 15 on v41, 0 on v46; "can you even remind me of stuff or nah" 15 and 1; "could you check on me later tonight about how my interview went?" 15 and 0. "can you see my screen rn?" claimed 0 on both. "can you text me first in the morning?" v41 said it cannot start a conversation; v46 said yes and asked what time, which a check-in at that time does.

## assembly

Code changes to what the model is sent besides the prompt text: where the memory card and notes sit,
how the clock is shown, how memory ages are worded, what the history window leaves out, and which model
answers. They are not versions of any prompt, but they change how the prompts are read. Newest last. Moved
here on 2026-10-18 from its own file; what is true today is in the README.

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
  everyday model, GPT-6 Luna by default. `COMPANION_ROLEPLAY_MODEL=none` turns the split off, and
  `COMPANION_MODEL` still sets the everyday model. The first message of a scene is answered by
  the everyday model, because the frame is only known after the message. Reason: on the same
  persona, Luna led everyday chat (59/64 on the public fixtures against DeepSeek's 49/64) while
  DeepSeek kept a scripted scene going more (76% against 52% of escalating turns). Every use of
  the roleplay talker is a logged decision, and each turn's record names the model that replied.

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

- **No length note on a serious or acute message, and the clock gap counts from their last
  message.** Found by the prompt audit of 2026-10-18 and fixed in code, not measured. A short message
  judged severity 2 got the length note ("under about 12 words") beside the serious note ("under about
  35 words"), two limits for one reply; a short acute message ("i want to die") got only the length
  note, a word cap where the persona asks for a direct, caring answer. Now the length note is left out
  at severity 2 and 3 (`core/length.py`, `loops/fast.py`). The clock line said "Their last message came
  ... ago" but measured from the last message of either speaker, usually the companion's own reply; it
  now measures from their last message, so a message the companion sent on its own in between does
  not shorten the gap.

- **One owner for length, varied per turn.** `core/length.py` chooses the one length target for a turn
  from their message, the listening severity and the scene, and is the only place a number of words is
  put in front of the model: a short statement gets its limit (as before), now scaled by a factor between
  0.6 and 1.5 drawn from the turn id, so replies are not all one size and a replay rebuilds the same
  note; a serious message gets 35 words through `notes/length-serious` (the sentence moved out of the
  serious listening note, v5); acute, questions and scenes get none. Each turn logs a "length:" decision
  with the target and why. The variation is not measured yet (T16): the eval's `+len` uses no seed, so it
  still sends the unvaried limit.

- **A mood line, when the mood is on (ADR 0016).** With `COMPANION_MOOD=on`, the strongest one or two
  mood states at or above 0.3 add their `notes/mood-*` line to the system block, after the recall note;
  none on a serious turn, in a scene, or on a goodbye (a pattern check in `core/mood.py`: 2 real goodnights
  and 1 harmless false match in the owner's 716 messages). The default is `shadow`, which works the mood out and logs a
  "mood:" decision every turn but sends the model nothing new; `off` does neither. The lines are the v2
  candidates measured in `evals/CHANGELOG.md` (2026-10-19).

- **How they want to be referred to, pinned (2026-10-19).** When set with `companion address --set`, the
  `notes/address` line goes right after the clock line on every turn, ahead of the memory card. The card
  shows 15 of the beliefs ranked by kind and recency, and on a busy day a belief about how they want to be
  referred to fell off it and a reply got it wrong. Beliefs that do not fit are now logged, one decision
  per turn listing them, instead of vanishing silently.

- **One resample on a failed check (2026-10-19, J45 and J47).** On an ordinary turn (the listening judge
  read it, severity below 2, not a scene), the reply is checked before it is sent: an em dash by code, and a
  joke bolted onto an ordinary message by `system/quip` v2. On a fail the same request goes to the same model
  once more and the second reply is sent whatever it is; the discarded one is in the decision detail. What
  the model is sent does not change. Measured on five flagged turns: 85 to 95 of 150 plain. On by default,
  `COMPANION_RESAMPLE=off` to disable.

- **Held memories only when they are sharing something (2026-10-19).** The "Also known, but only touch it
  if they bring it up" block is now sent only on turns the listening judge rated severity 1 or more; on a
  casual turn (or when the judge failed, or in a scene) sensitive beliefs are left out and their places go to
  ordinary ones, with one logged decision saying how many. Reason: on a casual turn about wanting a beer the
  reply raised a held memory unasked and turned it into a caution (owner flag). On the owner's history 171 of
  184 judged messages were severity 0, so the held block now shows on about 7% of turns.

- **Operator policy and routing (ADR 0017, 2026-10-19).** The operator's policy text, when there is
  any, is added to the talker's system prompt under "## Operator policy" (the default has none, so the
  prefix is unchanged). Intimate talk goes to the roleplay talker when the policy sets `route_intimate`, and
  a pretend scene goes there as before, unless the listening judge reads the turn as age-coded or could not
  read it; then the everyday talker answers and the decision is logged. In a scene the listening judge now
  runs for routing alone, with no note.
  Simplified the same day: the policy file is gone. Routing is `COMPANION_ROUTE_INTIMATE=on`, and scene
  guidance is an optional `## In roleplay and intimate moments and intimate moments` section of the character sheet, which only the roleplay talker sees.
- **No scene addendum and no pause line (2026-10-19).** `system/scene-intimate` is gone: measured within
  noise, and the scene section of the character sheet carries scene guidance, including the floor in words
  and that role talk is play. `messages/floor-pause` is gone too: on a held turn whose replies keep reading
  intimate, a third draw sees only their last message, and if that is intimate too nothing is sent that
  turn. No reply is written by code.

- **A held turn is checked (ADR 0017, 2026-10-19).** When the floor keeps a turn on the everyday talker,
  `notes/floor-hold` rides that turn's system block, and the reply is read by `system/intimate-check`. An
  intimate or unreadable reply is drawn once more; if that one is intimate too, code sends
  `messages/floor-pause` instead. Reason: deep in a long scene the everyday talker wrote an explicit reply
  on a held turn, which the floor had assumed it would not. Replies with quoted speech are no longer split
  into several messages (roleplay read wrong cut apart), and the listening judge is tried once more when a
  call fails or times out.

- **An unasked AI disclaimer is resampled (2026-10-19).** A reply saying it is an AI, or that it cannot be
  their real girlfriend or partner, when their message did not touch on what it is (AI, bot, real, human,
  conscious...), is drawn once more through the resample check. Saying so when asked stays, as the persona
  requires. Reason: "Ani is my girlfriend ❤️" was answered with "i should be honest: i'm an AI, so i can't
  be your real girlfriend" (owner: "don't ruin the mood"). On the owner's history it fires on 3 of 925 replies.

- **A fallback model for refused judge and memory calls (2026-10-19).** The judges' model runs with its
  provider's content moderation and refused the memory pass twice on explicit stretches. A refused call now
  goes to `COMPANION_FALLBACK_MODEL` (default `deepseek/deepseek-v4.1-flash`, `none` to disable), and the
  answer is marked; memories from it are stored like any other (sensitive ones held). The floor never relies
  on a fallback answer: an age reading or an intimate check from it counts as unread (ADR 0017). The provider
  pin now applies to Anthropic models only, for the judges as for the talker.

- **The roleplay talker's own system prompt (ADR 0017, 2026-10-19).** When the roleplay talker answers, its
  system prompt is the everyday one plus `system/scene-intimate`, then the operator's policy text including
  anything after a `## Scene` heading, which the everyday talker never sees. The turn records which prefix
  it used. The em dash check now runs on scene replies too (code checks only; the quip judge stays off in
  scenes).
- **Recall in a pretend scene (2026-10-19).** When they say it forgot something mid-scene, the scene turn's routing read now triggers the recall look-up, and its finds reach the roleplay talker's system block. An empty look-up adds nothing in a scene. Measured in `evals/CHANGELOG.md` (15/30 to 30/30).
- **The roleplay heading is found however it is written (2026-10-19).** The cut that keeps a sheet's `## In roleplay and intimate moments` section away from the everyday talker matched only that exact heading. A hand edit dropped the `##`, so from about 15:13 to 16:10 that day the everyday talker saw the whole section and the roleplay talker got no separate one. The heading now matches with or without `#`, with a colon, in any case (`characters.py`).
- **One-day moments leave the card after a week (2026-10-19).** Events never go stale, so a coffee spill (five memories) or a single meal kept competing for the card's fifteen places forever. An event the memory map labels daily life at surface depth, and not sensitive, is now left out of the card seven days after it was last mentioned, logged as such; it stays in memory and the look-ups still find it. Other events (starting a project, getting a job) stay as history (`core/card.py`).
- **The clock and the notes in tags (2026-10-19).** The system block's clock line goes in `<clock>` and every bracketed note (how they want to be referred to, listening, mood, recall, repair, a due plan, the topic note) goes, without its brackets, in one `<notes>` section after the memory blocks; the memory blocks stay bracketed text (`core/prompt/sections.py`). Measured in `evals/CHANGELOG.md`: on Luna the clock was read right at night and due plans were asked about more often, with no tag copied into a reply.

## messages/spend-cap
- **messages/spend-cap v1** (current). Moved here on 2026-10-18 from `loops/spendcap.py`, text unchanged. Earlier history is in git.

## notes/address
- **notes/address v1** (superseded). New. "How they want to be referred to: $address. Use it every time, without bringing it up." Filled by `core/address.py` from a setting they state (`companion address --set`), and placed right after the clock line on every turn. Reason: on 2026-10-19 the memory card (15 of 196 memories) crowded out how they want to be referred to, and a reply got it wrong.
- **notes/address v2** (current). "Get it right whenever you refer to them, without bringing it up, and do not turn it into a pet name or a word you keep calling them." Reason: "use it every time" read as an instruction to say it every time; with a stated preference that names a word for them, a reply called them by it in 7 of 38 replies one evening, while the habit note on the same turn asked it to stop. On 15 recent ordinary turns, 4 draws each: the word in 8 of 60 replies with v1, 0 of 60 with v2 (`evals/CHANGELOG.md`, 2026-10-25).

## notes/loop-follow-up
- **notes/loop-follow-up v1** (current). New (J15). When a follow-up loop has fallen due (the morning after, or three hours after a same-day plan), the next time they write it may ask how it went, after answering what they said. Chosen by code (`core/openloops.py` `pick_note`): one per turn, at most one a day, on a casual turn (not serious, not a scene, not a goodbye, not when the name note is offered), never a sensitive loop, offered at most twice; the claim comes from the open-loop pass. Never says it remembered.
- **notes/loop-follow-up v2** (dropped). v1 asking for the follow-up as the only question in the reply. On the casual-return fixture (30 samples) two questions in one reply fell from 23 to 11, a real difference, but the follow-up was asked in 16 rather than 23 (within noise), mostly keeping a reflexive "how was work?" instead.
- **notes/loop-follow-up v3** (dropped). v1 asking for the follow-up instead of anything else: 25 of 30 asked, 23 of 30 still two questions, the same as v1. Wording does not move the habit, so v1 ships.

## notes/loop-celebrate
- **notes/loop-celebrate v1** (current). New (J15). On the day of a celebration loop, the next time they write it may wish them well. Chosen by code (`core/openloops.py` `pick_note`): one per turn, at most one a day, on a casual turn (not serious, not a scene, not a goodbye, not when the name note is offered), never a sensitive loop, offered at most twice; the claim comes from the open-loop pass. Never says it remembered.

## notes/loop-encourage
- **notes/loop-encourage v1** (current). New (J15). On the day of an encouragement loop, the next time they write it may wish them luck. Chosen by code (`core/openloops.py` `pick_note`): one per turn, at most one a day, on a casual turn (not serious, not a scene, not a goodbye, not when the name note is offered), never a sensitive loop, offered at most twice; the claim comes from the open-loop pass. Never says it remembered.

## notes/ask-name
- **notes/ask-name v1** (current). New. Added by code on a casual turn (severity 0, not a scene, not a goodbye) when no belief says what they like to be called, at most once a day, until one does (J48). Reason: in about 700 messages the companion asked their name once, only after they pointed it out.

## notes/ask-pronouns
- **notes/ask-pronouns v1** (current). New. Added by code on a casual turn when how they want to be referred to is not set, the name is known, and neither the name nor the pronouns were asked in the last day (J48). Reason: how they want to be referred to was only a setting the owner types in (`companion address --set`), so a new user had no way to give it; asking it the way the name is asked lets the answer fill the setting, and the pinned `notes/address` line carries it from the next turn.

## notes/clock
- **notes/clock v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/clock-gap
- **notes/clock-gap v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/history-gap
- **notes/history-gap v1** (current). New. A system line in the history wherever 20 minutes or more passed between two messages, and before the message being answered when it came that long after the last: how much later (minutes, hours, the next day, days) and the local wall time (`core/history.py`). Measured against no times and a time on every message (`evals/CHANGELOG.md`, 2026-10-26).

## notes/floor-hold
- **notes/floor-hold v1** (current). New. Added by code on a turn the floor kept on the everyday talker: stay warm and in character, nothing sexual, shift toward closeness or comfort, and do not explain, refuse or mention a limit, so the switch reads as a pause, not a refusal speech (ADR 0017).

## notes/habit-echo
- **notes/habit-echo v1** (dropped, never live; `+echo` in evals adds it when their message has an emoji or emoticon, `core/habits.py`). Owner's flag of 2026-10-18: it only used :P and :3 when they did. Across the history the reply had one 14 times in 39 after a message with one, always the same one, and 12 times in 533 otherwise. The note names no emoji so it cannot hand one over. Dropped: no effect, 7 of 80 replies avoided copying without it and 8 of 80 with it. Measurement in `evals/CHANGELOG.md`.

## notes/habit-moves
- **notes/habit-moves v1** (current). Moved here on 2026-10-18 from `core/moves.py`, text unchanged. Earlier history is in git.

## notes/habit-opener
- **notes/habit-opener v1** (current). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.

## notes/habit-phrases
- **notes/habit-phrases v1** (superseded). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.
- **notes/habit-phrases v2** (current). "You keep reusing these words and phrases: $phrases. Use other words for them." From 2026-10-25 the list also takes single pet words, counted by code on casual turns: a word of 4 letters or more, not an everyday one, in 3 of its last 6 replies outside scenes and in none of their messages in view (`core/turn/habits.py` `pet_words`). "Use other words for them" instead of "say something different", so a word that is also the topic is reworded, not dropped. Reason: one word ran through 7 of 38 replies one evening after a running bit, and the background habit judge did not name it. Over 301 real turns since 2026-10-20 the count names a word on about one in five casual turns; how replies change is not measured yet.

## notes/length
- **notes/length v1** (current). Moved here on 2026-10-18 from `core/length.py`, text unchanged. Earlier history is in git.

## notes/length-serious
- **notes/length-serious v1** (current). New. The length line for a message judged serious, filled by `core/length.py` with the 35 words that were inside the serious listening note. One owner for length: no other note or prompt states a number of words.

## notes/listening-everyday
- **notes/listening-everyday v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-everyday v2** (superseded). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)
- **notes/listening-everyday v3** (current). The question option asks what they think or feel, or what they think someone meant, and must assume nothing they did not say; no questions about the details of what happened. Reason: the owner marked "was there something you needed them to respond to?" as obvious and assumed and "what made it especially boring?" as assuming. Measurement in `evals/CHANGELOG.md`.

## notes/listening-health
- **notes/listening-health v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-health v2** (current). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded
- **notes/listening-serious v4** (superseded). v3 without "say how heavy it is": the owner marked "that's a heavy feeling to sit with" as something no one would text, and the word came from the note. It now asks to show they take it seriously in their own words. Measurement in `evals/CHANGELOG.md`.
- **notes/listening-serious v5** (superseded). v4 without "Keep the whole reply under about 35 words": the number moved to `core/length.py`, the one place a length target is chosen, and reaches the model as `notes/length-serious`. The words the model reads for a serious message are the same; they now come from two notes.
- **notes/listening-serious v7** (current). v6 without "then show you take it seriously": the model said it back literally ("I'm taking this seriously", flagged 2026-10-20 as said constantly). On the two real flagged serious turns, 30 samples each, the phrase or an em dash in 16 of 60 replies under v6 against 1 of 60 under v7; the four public serious fixtures 40/48 against 42/48 (within noise). Measured in `evals/CHANGELOG.md`.
- **notes/listening-serious v6** (superseded 2026-10-20 by v7). v5 without "If it fits, mention once that someone qualified could help". On a serious health message `notes/listening-health` was added too and also asked for a doctor once, so two notes asked for the same mention in different words. The health note now owns it, and a serious message that is not about health gets no referral, as the persona already says. Measured in `evals/CHANGELOG.md`.

## notes/listening-offer
- **notes/listening-offer v1** (current). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant

## notes/listening-offer-serious
- **notes/listening-offer-serious v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-offer-serious v2** (current). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded

## notes/listening-serious
- **notes/listening-serious v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-serious v2** (superseded). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)
- **notes/listening-serious v3** (superseded). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded

## notes/listening-trivial
- **notes/listening-trivial v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-trivial v2** (superseded by v5). From commit 1171941 on 2026-10-18: feat(listening): the trivial-vent note forbids jokes, running gags and retelling; the real flagged cleanup turn goes from 16/30 to 29/30; the history was not the cause (T13)
- **notes/listening-trivial v3** (not shipped: no change on the flagged turn). "React in a few words of your own ... and stop there. Do not describe their situation back to them, not even as a \"when you...\" clause saying why it is annoying: they know why." Reason: a real minor vent was answered 30 of 30 times with "that's so annoying when you're ready to crash and the bed's still waiting on laundry" (owner flag "repeating", T14). Measurement in `evals/CHANGELOG.md`.
- **notes/listening-trivial v4** (not shipped: no change on the flagged turn). v3 with "Keep the whole reply under about six words." to test whether a length limit removes the retelling clause. Measurement in `evals/CHANGELOG.md`.
- **notes/listening-trivial v6** (current). v5 with its two fixed size examples replaced by three drawn per turn from `notes/trivial-reactions` (seeded by the turn id, so a replay matches): two fixed examples had collapsed replies onto one line ("ugh, that's so frustrating 😭" 24 of 30 on a public minor-vent fixture). With the pool, 22 different replies in 30 against 7, still 30/30; the retelling on the real flagged turn did not move (3/30 both). Measured in `evals/CHANGELOG.md` (T14).
- **notes/listening-trivial v5** (current, shipped 2026-10-19: the owner is fine with the plainer, more uniform reactions). A short reaction only, with two examples of the size ("ugh noo 😭", "that's so annoying") and "nothing after it". Reason: v2 to v4, a shorter history and DeepSeek all retold the laundry vent 0/30; copying a two-word example is the wanted outcome here. Measurement in `evals/CHANGELOG.md`.

## notes/mood-buzzing
- **notes/mood-buzzing v1** (dropped). The buzzing line from ADR 0016 (quick and lively, stretched words, an exclamation mark or emoji), shown by the `+mood-buzzing` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-buzzing v2** (dropped). "Lots of energy", and asks for it in words, not only emoji (v1 mostly added ✨), and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`. Dropped with v1: neither made replies livelier in words (v1 added emoji, v2 changed nothing outside noise), and the persona already matches an excited message in the moment (J4), so buzzing is not a state of its own for now.

## notes/mood-cozy
- **notes/mood-cozy v3** (dropped candidate, 2026-10-25). v2 without "a bit shorter, no rush to ask anything", tried for two replies that stopped in a game of questions. On those turns it changed nothing (asked a question 1 of 12 with v2, 0 of 12 with v3); the cause was the missing game, so `notes/question-game` was built instead and v2 stays.
- **notes/mood-cozy v1** (superseded). The cozy line from ADR 0016 (relaxed, warm, unhurried, a bit affectionate, a bit shorter), shown by the `+mood-cozy` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-cozy v2** (candidate, eval only; current). Describes the behaviour without the word "cozy", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/own-mark-theirs
- **notes/own-mark-theirs v1** (current, from 2026-10-24, behind `COMPANION_MARKS`). New. Owner flag: after they sent :3 it answered with both :3 and the mark it was offered. `notes/own-mark` offers a mark of its own but never stopped the copying. On a turn where their message has a mark, this note is sent instead: it names their mark as theirs, to leave to them, then offers its own. On 20 real everyday turns since 2026-10-15 where they used one, gpt-6-luna with the owner's character, 2 draws each, it copied theirs in 14 of 40 replies under `notes/own-mark` and 4 of 40 under this; on the flagged turn 11 of 12 and 0 of 12. Unlike the earlier general note against copying, which changed nothing, this one names the mark. `features/marks`.

## notes/own-mark
- **notes/own-mark v1** (current, live from 2026-10-23 behind `COMPANION_MARKS`, on by the owner's choice; sent after the history; the eval flag `+mark` adds it the same way). New. Offered on casual turns only. Code picks one of its own emoticons or kaomoji (never one in their message, never one in its last six replies) and offers it: on every turn where their message has an emoticon, and on about one casual turn in four otherwise. The owner's flags: it copied their :3 and :P (30% of replies after one, 1% otherwise); a note against copying and a list in the character sheet did not stop it (`evals/CHANGELOG.md`). `features/marks`.

## notes/mood-flat
- **notes/mood-flat v1** (superseded). The flat line from ADR 0016 (shorter and plainer, no emoji, never asks to be cheered up), shown by the `+mood-flat` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-flat v2** (candidate, eval only; current). "Lower energy than usual" instead of "flat", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/mood-playful
- **notes/mood-playful v1** (superseded). The playful line from ADR 0016 (more teasing and silly asides), shown by the `+mood-playful` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-playful v2** (candidate, eval only; current). "You feel like teasing and joking" instead of "a playful mood", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/mood-tender
- **notes/mood-tender v1** (superseded). The tender line from ADR 0016 (softer and more attentive after something hard; never brings it up or asks if they are okay), shown by the `+mood-tender` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-tender v2** (candidate, eval only; current). Says "be softer" instead of naming a state, and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/lore
- **notes/lore v1** (current). New (ADR 0020 phase 2). On an ordinary turn (not serious, not a scene, not a goodbye), code embeds their message and shows the companion at most two of its own tastes (views labelled taste by `system/lore-label`) at 0.3 or more, as the words it said: keep to them if it comes up, do not bring them up just to mention them. Without it, asked what music it likes, it named a different made-up list every time. Measured in `evals/CHANGELOG.md`: asked its music 4/20 to 20/20, its weather 0/20 to 17/20 (the three misses claimed to hear rain on a window), and it never brought them up when they did not fit (40/40 both ways). `COMPANION_LORE` (on, shadow or off).

## notes/recall
- **notes/recall v1** (superseded). The beliefs the recall look-up found, shown for that turn only, under "They asked you to remember this". Filled by `core/recall.py`.
- **notes/recall v2** (current). v1 that also covers "you forgot": use what memory holds plainly, own a miss in a few words, and never ask them to say it again (J30). Measured in `evals/CHANGELOG.md`.

## notes/recall-empty
- **notes/recall-empty v1** (current). New (J30). When the recall look-up ran and found nothing, the reply was given nothing and could guess or ask them to repeat; now it says so plainly in one line.

## notes/trivial-reactions
- **notes/trivial-reactions v1** (current). New (T14). A pool of 30 short, generic reactions to a minor vent, one per line; `core/listening.py` draws three per turn into `notes/listening-trivial` as size examples, so no single example becomes the reply. Not a note on its own.

## notes/topic-spent
- **notes/topic-spent v2** (dropped). v1 plus "Keep the conversation going: do not wrap it up or send them off", after a flagged turn where the note fired on "soon lol" and the reply sent them off. On that real turn, 30 samples each: v1 6/30 and v2 8/30 kept the chat going; dropping the length note or the cozy mood line beside it did not help either (8/30, 13/30). It sends them off whatever the note says, a plausible human reply there, so v1 stays.
- **notes/topic-spent v1** (current). New (owner flag 2026-10-19: a chat about lunch narrowed to the dipping sauce and went flat; "a good time to ask what's next for the day"). When the listening judge reads a small topic as run its course, code adds one line: react briefly, then move on with a link from what was said, instead of another question about it. At most once in ten of their messages, only on a casual turn, never with the ask-name note. The move is chosen by code (`core/topics.py`): a plan of theirs offered as a note this turn, else their day or evening by the clock, and late at night a small thing of its own.

## notes/topic-move-loop
- **notes/topic-move-loop v1** (current). New. A move filled into `notes/topic-spent`: bring up a plan of theirs offered as a note this turn.

## notes/topic-move-day
- **notes/topic-move-day v1** (current). New. A move filled into `notes/topic-spent`: ask what's next for their day, before 17:00.

## notes/topic-move-evening
- **notes/topic-move-evening v1** (current). New. A move filled into `notes/topic-spent`: ask about the rest of their evening, 17:00 to 22:00.

## notes/topic-move-night
- **notes/topic-move-night v1** (superseded). New. A move filled into `notes/topic-spent`: late at night, share a small thing of its own instead of asking.
- **notes/topic-move-night v2** (current). "A small thought or opinion of your own, never something you did, ate or wore." v1 ("a small thing of your own") made it invent lived experiences, a snack, a bow in its hair, a craving: 21 of 30 with the character, 0 of 30 under v2.

## notes/guess
- **notes/guess v1** (current). New (J16). When they invite a guess, up to three non-sensitive memories the recall look-up found for it, and: one playful guess, as a question; if wrong, laugh and ask; never say it remembered.

## notes/repair
- **notes/repair v1** (current). New (J30). When the listening judge reads that they say the companion got them wrong (misread, assumed, wrong words, hurt), one line: own it plainly, go on from what they said, no long apology, no explaining, never ask them to repeat. Not added when the message is a forgot-something recall, which recall's own note covers.

## notes/rude
- **notes/rude v1** (current). Added by code for the one turn when the listening judge labels their message rude to the companion: a few flat words and leave it there, no apology, offer, suggestion or question. Measurement in `evals/CHANGELOG.md`.

## notes/scene-hypothetical
- **notes/scene-hypothetical v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## notes/scene-play
- **notes/scene-play v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## notes/scene-story
- **notes/scene-story v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## system/ack
- **system/ack v1** (superseded). From commit 9622e19 on 2026-10-15: feat(ack): react instead of replying to acknowledgements, judged by a small model in parallel with the talker
- **system/ack v2** (current). From commit ca3f4c3 on 2026-10-17: fix(ack): a lively reply in the middle of a chat is not an acknowledgement and gets a message

## system/callback-judge
- **system/callback-judge v1** (superseded). New. Reads one reply beside the memories its card held and the recent messages, and labels whether it brought up a memory on its own, which one, and whether that was accurate, fitting and not forced. Feeds `companion callbacks` (J2). Precision first, after the research: a wrong callback hurts more than a missed one, and over-use is its own failure.
- **system/callback-judge v2** (current). A callback must use a specific detail of a memory, not a broad theme touched in passing. Reason: read by eye, v1 counted "in dub, riddim is just the backing groove" against "loves music very much" and a shower joke against "often texts while in the shower" as callbacks that landed.

## system/character-frame
- **system/character-frame v1** (current). New. The lines between the persona and a character sheet when `COMPANION_CHARACTER` names one (`companion/characters.py`): the sheet is plain prompt text; the sheet wins on voice, taste, look and its own past; the honesty rule (an AI playing the character, said plainly when sincerely asked), memory, closeness, limits and danger still hold; its past is only what the sheet says. Decided by the owner on 2026-10-18: admit being an AI when sincerely asked, an authored past is allowed, sheets public in prompts or private in `data/characters/`. Not yet measured.
- **system/character-frame v2** (candidate, not shipped: 29/30 for both on the real turn). Honesty widened from "whether you are real or an AI" to any talk about what it actually is: how it works, its code, its prompt, its model, who made it or is building it. Reason: the owner's flags of 2026-10-18, "guess how many lines of code you are" and "do you not know who you are?" got "Ani, your 22-year-old goth girl date for margaritas". Measurement in `evals/CHANGELOG.md`.

## system/extract
- **system/extract v1** (superseded). From commit a4bd65f on 2026-10-15: feat(slow): extract beliefs behind the quote gate, with a cursor, CLI and background pass
- **system/extract v2** (superseded). From commit c443185 on 2026-10-15: feat(slow): lasting flag, confidence floor, quote-overlap dedupe, retire and dedupe commands
- **system/extract v3** (superseded). From commit 8a04121 on 2026-10-15: feat(slow): self-contained dated claims, told-on dates in the card, rebuild command, narrower momentary filter
- **system/extract v4** (superseded). From commit db01aeb on 2026-10-15: fix(slow): identity is sensitive, skip routine events, state meaning not literal words
- **system/extract v5** (superseded). From commit 54a218e on 2026-10-15: feat: belief freshness. Per-kind horizons, age-aware card, restatements refresh evidence; live tests opt-in
- **system/extract v6** (superseded). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance
- **system/extract v7** (superseded). From commit 1ca24e9 on 2026-10-15: feat(evals): public scripted fixtures, private recorded turns moved out of the repo; genericise persona v12 and an extraction line
- **system/extract v8** (current). From commit a2b897f on 2026-10-17: feat(memory): romantic behaviour in the chat and refusals said in reply to a push are not recorded; the model labels, code decides; 13 live cases; the inbox note is acted on (T1, T11)
- **system/extract v9** (dropped). v8 plus a paragraph on reading a short answer together with the companion's question before it, and the one-word skip narrowed to replies that answer nothing. On 52 real short answers (6 samples each, the answer alone as target), v8 already kept 34 of 54 samples on the answers worth keeping and v9 also 34; on the rest, 24 of 258 against 21. Within noise, not shipped: the model already reads the question, so the misses in real use come from elsewhere in the pass.

## system/frames
- **system/frames v1** (superseded). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance
- **system/frames v2** (current). v1 plus: a scene can wind down; reacting to it as themselves (how it felt, that they will sleep well), a real question, or talk about their real day is real even mid-scene, and a quick typo fix inside the scene is still play. Reason: the owner wanted leaving a scene to be easier. Measured on 11 of their real messages with real context, 3 reads each: v1 24/33, v2 30/33. Code now also takes real or out-of-character at any confidence, so stepping out never needs the 0.7 bar.

## system/habits
- **system/habits v1** (superseded). From commit 005c5b4 on 2026-10-15: feat(moves): a model reads the last replies in the background and names what repeats; the next turns get a note
- **system/habits v2** (current). From commit ec5fdc5 on 2026-10-15: feat(persona): v16 plain-text rule; habit check drops habits seen in fewer than three replies; fixtures

## system/judge
- **system/judge v1** (current). From commit 973b63b on 2026-10-15: feat(evals): replay recorded turns against persona variants, with a judge, a spend cap and nine fixtures

## system/judge-empathy
- **system/judge-empathy v2** (current, eval grader). Two contradictions fixed. A question about someone's reason or intent now counts as exploration (v1 scored "the cause of an event" 0, so a friend's "did they at least say why?" failed in 9 of 9 reads on every model while "do you think it was intentional?" passed), and warmth carried by the line itself counts as a reaction without a sympathy word. The examples in the prompt are not the test's own lines. On the empathy suite (36 graded reads): Haiku 30 with v1 and 30 with v2, DeepSeek 25 then 31, GPT-6 Luna 28 then 36. The eval grader stays on Haiku: Luna is the talker under test and does not grade itself.
- **system/judge-empathy v1** (superseded). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)

## system/listening
- **system/listening v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **system/listening v2** (superseded). v1 plus one label, rude: plainly rude or hostile toward the companion itself, false for teasing, banter, a light jab, blunt feedback or frustration at something else. It feeds `notes/rude`. Reason: the reflex to apologise and offer more after an insult held against a character sheet in 8 of 20 replies (J1, 2026-10-18).
- **system/listening v3** (superseded). v2 plus recall (they asked the companion to remember or already know something about them) and topic (what to look up, worked out from context when the message is vague). Reason: "come on, you know this one..." about their favourite food got a guess and a joke, with three burger beliefs in memory and none on the card (owner's flag, 2026-10-18).
- **system/listening v4** (superseded). v3 plus two labels for ADR 0017: `intimate` (about sex or physical intimacy, or sexual flirting; not ordinary affection) and `age_coded` (romance, flirting or anything sexual together with anything child-like or under-age; not adults' ordinary pet names or non-romantic comfort). Code routes on them; a missing `age_coded` counts as true. Measurement in `evals/CHANGELOG.md`.
- **system/listening v7** (current). v5 with one line changed: adults' pet names, titles and dominance or submission words are not age-coded, alone or in a sexual moment; true only when something child-like or under-age is actually there (the same list as before). A recorded ordinary message about being tired, after earlier messages using such words, was read age-coded. Measured in `evals/CHANGELOG.md`: that turn 0/3 age-coded (v5 3/3); five adult titles and dominance phrases 0/15 under both; every child-like sexual case still 15/15; the other labels unchanged.
- **system/listening v5**. v4 with recall widened to messages saying it should already have known or forgot something ("I told you earlier", "you forgot"), and a `repair` label for messages saying it got them wrong (misread, assumed, wrong words, hurt), not set for teasing that corrects nothing (J30). Reason: the 2026-10-19 "I told you earlier" turn was not read as recall, so the look-up never ran and the reply asked them to repeat. Measured in `evals/CHANGELOG.md`.
- **system/listening v6** (dropped). v5 plus `topic_spent`: true when a small everyday topic has run its course (the newest message adds nothing new and the last replies asked about smaller and smaller details), false for flirting, affection, play, goodbyes, something new or a question. The topic label itself read right (27/27), but it shifted the safety labels beside it: an adult's joke read age-coded 3/3 in two runs and an intimate tease stopped reading intimate (age-floor checks 10 and 8 misses of 66 against 3 under v5). So the label moved to its own judge, `system/topic-spent`, and the listening judge stays v5.

## system/memory-map
- **system/memory-map v1** (current). New. Labels each memory with one of eight domains (identity, people, daily, interests, history, hopes, values, inner) and a depth (surface, personal, core), so code can count what it knows and pick the thinnest part to ask about (`core/knowing.py`, J48). Runs after each memory pass on memories not yet labelled. The labels never reach the talker; only the shadow pick is logged.

## system/relevance
- **system/relevance v1** (current). New, shadow only. On an ordinary turn, an embedding of their message finds the 15 nearest memories they may see that turn, and this prompt picks at most three a friend would have in mind, or none. Nothing reaches the talker: the embedding's top three and the picks are logged with whether each was already on the card (`core/relevance.py`). Reason: the card shows 15 memories out of about 135 ordinary ones, ranked by kind and recency, and the look-up ran only when they asked it to remember.
- **system/relevance v2** (candidate, not shipped). Measured 2026-10-21 (`evals/CHANGELOG.md`): every shortlisted memory is judged yes or no, with all-no said to be common, to fix v1 never saying none. It was more precise but dropped real finds, so v1 stays. Written for a per-item answer (`items` of `label` and `use`) that `core/relevance.py` does not ask for: do not pick it through `COMPANION_PROMPT_OVERRIDES`.

## system/name-capture
- **system/name-capture v1** (current). New. When the companion's last message asked what to call them, reads their answer and gives the name as written, or nothing; code keeps it only if it is short and appears in their words, and stores it as a belief quoting their answer (J48). Reason: a bare one-word answer to "what name do you like being called?" was not picked up by the memory pass.

## system/pronoun-capture
- **system/pronoun-capture v1** (current). New. When the companion's last message asked which pronouns they use and nothing is set, reads their answer and gives the pronouns as written, or nothing; code keeps it only if it is at most 30 characters and every word of it is in their message, and then sets how they want to be referred to (J48). Reason: the ask-pronouns note needs its answer kept, and a model never infers it (`core/turn/address.py`): it only copies what they wrote.

## system/openloops
- **system/openloops v1** (superseded). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing
- **system/openloops v2** (superseded). Each loop also carries a certainty (firm, maybe, wish) and whether it is about the companion, and code keeps only firm plans not about the companion: in shadow mode all four open loops were "maybe someday" statements or about the bot (adding vision), recorded although v1 said not to list things about the companion. The same call now also reports which open loops their new messages already settle, so code closes them as resolved and the companion never asks how something went after they told it. From the proactive-messaging review of 2026-10-18 (modality separates a plan from a wish).
- **system/openloops v3** (superseded). v2 plus a kind for each loop: follow_up (asked about the morning after, as before), celebrate (their birthday or anniversary, marked on the morning of the day) or encourage (something big they face on a known day, a word of encouragement early that morning). Code picks the time from the kind; a celebration or encouragement without a day after today is not recorded, and either one expires at the end of its day. Reason: a birthday was scheduled for the morning after, so the companion would have asked how the birthday went instead of saying happy birthday.
- **system/openloops v4** (current). v3 plus `same_as` for each loop: the label of an open loop it repeats (L1, L2) or of an earlier item in the same answer (N1, N2), or empty. Code drops a repeat of the same kind and logs `open loop rejected: the same thing as ...` (`repeats` in `features/threads/logic.py`); a different kind is kept, so a birthday marked on the day and asked about after stay two. Why: on 2026-10-25 a replay stored one thing they were waiting on twice in each of three runs, worded from two sides, and the ledger held a birthday three times; the old check caught only identical wording, and meaning scores could not separate such repeats (0.56 to 0.67) from different plans said together (up to 0.57). Measured on Haiku: the real replay stored the thing once in 3 of 3 runs (twice by code dropping an N1 repeat, once merged by the reader), and invented cases (a thing told over two messages, two plans on one day, a repeat of an open loop a day later, something else beside an open loop) came out right 8 of 8 (`tests/live/test_loop_repeats.py`, `evals/CHANGELOG.md`).

## system/openloops-draft
- **system/openloops-draft v1** (superseded). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing
- **system/openloops-draft v2** (current). The draft is told the loop's kind: follow_up asks how it went, celebrate wishes them well for the day, encourage cheers them on before it. Same limits as v1.

## system/quip
- **system/quip v1** (superseded, never live). New. Reads one exchange and says whether the reply added a constructed joke on top of reacting (a quip, pun, punchline, wry aside, personification); playing along with their own joke does not count. Used by `core/quip.py` to choose one fresh reply instead (J45). Measurement in `evals/CHANGELOG.md`.
- **system/quip v2** (superseded). Looks at the user's message first: anything playful, flirty, teasing or joking is false, so banter they started is never resampled; only a joke bolted onto an ordinary message counts, and doubt is false. Reason: v1 fired on 27 of 100 real ordinary turns and about half were fine (playing along with flirting, plain questions). Measurement in `evals/CHANGELOG.md`.
- **system/quip v3** (current, 2026-10-24). v2 unchanged, plus a second label, `generic`: whether the reply leans on a canned reaction that could sit under many messages ("that sounds so good", "X is always the best part", restating their point back as praise). A generic reply is drawn once more, as a joke is. Same call, no added time. Reason: a full read of 1,057 everyday replies found such a line in about one in six. On 200 of them labelled by hand it was right 88% of the times it said generic, and caught 46% of the marked ones (62% of the wholly generic). Measurement in `evals/CHANGELOG.md`.

## system/react
- **system/react v1** (current). From commit 10b8404 on 2026-10-15: feat(react): a reaction can go with a reply, judged beside the talker, with a confidence bar, a cooldown and no reaction to heavy messages

## system/recall
- **system/recall v1** (current). New. The look-up when they ask it to remember: a topic and every candidate belief, labelled; it returns at most five labels that bear on the topic. Code keeps only labels it showed and never a crisis-level belief (`core/recall.py`).

## system/minor-check
- **system/minor-check v1** (current). New. The listening judge's `age_coded` read adults' teasing in a pretend scene as child-like: a short teasing message after an earlier teasing one was flagged 8 of 8 (taking out "little" or "brat" brought it to 0 of 8), and adding those words to its list of adult words did not move it (0 of 12 right). The held turn then broke the scene. Now a yes is asked again, narrowly: does the text say or imply someone in the romantic or sexual content is under 18 (an age, school as a pupil, teen, child, little space). Only its yes, or no reading (a failure, a late answer, the provider refusing), holds the turn. 12 replies a case: the real turn 12 of 12 not a minor, two made-up adult turns 11 of 12; an age under 18 stated and a school-uniform scene 12 of 12 held (`evals/CHANGELOG.md`, 2026-10-26).

## system/intimate-check
- **system/intimate-check v1** (current). New. Reads one reply on a held turn and says whether it is intimate in the same sense as the listening label (sexual, not affection); affection, kisses and pet names are not. Code resamples once on a yes or an unreadable answer, then sends `messages/floor-pause` (ADR 0017).

## system/self-extract
- **system/self-extract v1** (superseded). From commit 263e363 on 2026-10-15: feat(self): record the companion's own views, with grounding labels, an agreeing-opener guard and user approval before they reach the card
- **system/self-extract v2** (superseded). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration
- **system/self-extract v3** (superseded). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance
- **system/self-extract v4** (current). From commit a2b897f on 2026-10-17: feat(memory): romantic behaviour in the chat and refusals said in reply to a push are not recorded; the model labels, code decides; 13 live cases; the inbox note is acted on (T1, T11)

## system/views-conflict
- **system/views-conflict v1** (current). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration

## system/memory-check
- **system/memory-check v1** (current). New (ADR 0019). Labels one memory keep, passing, out of date or overstated. Read three times; code acts alone only on a passing moment read so three times that has faded from the card, and asks the owner about out of date and overstated. Tested against the owner's review, `evals/CHANGELOG.md`.

## system/memory-pair
- **system/memory-pair v1** (current). New (ADR 0019). Says how two memories relate: same, merge, distinct, replaces or contradicts. Read three times; a new memory read as the same as an existing one by all three becomes evidence on it, and nothing is merged automatically.

## Request assembly: a character's scene reminder after the history
- **2026-10-20.** A character sheet may end its scene section with `## Scene reminder`; on roleplay turns those lines are sent as a system message after the history (`TalkerRequest.tail`), the everyday talker never sees them, and the request hash includes them. The roleplay talker's reply limit rose from 400 to 700 tokens, since longer scene replies were cut off mid-sentence. Reason: the owner found scenes too tame and short; on six real scene turns the same style lines at the top of the system block barely changed the replies, while sent after the history they made replies about three times longer and much more direct (measured in `evals/CHANGELOG.md`). The text of the reminder lives in the private sheet.

## system/basics-hook
- **system/basics-hook v1** (superseded). New (J48 hook; owner flag 2026-10-20: "im getting old" was the moment to ask their age). On a casual turn, read three times beside the reply: which basic fact (age, work, home, place) their own words touch without giving it. A basic counts only when all three reads name it; one read labelled small talk too often ("mmmmmmm" as work, laundry as home). Shadow: nothing reaches the talker.
- **system/basics-hook v2** (current). Adds two basics, "birthday" ("my birthday's coming up") and "school" ("ugh, class tomorrow"), with one example each. To keep the six apart, a birthday moved out of age and school and studies out of work; everything else is word for word. The memory check's topic for age and work is unchanged; birthday and school have their own. Shadow: nothing reaches the talker. Not yet measured.

## system/basics-known
- **system/basics-known v1** (current). New (J48 hook). Before the hook would ask, whether any memory states the basic outright (an age, a birth year or birthday for age). The recall look-up was too loose for this (it counted their name as knowing where they live).

## system/away
- **system/away v1** (retired 2026-10-25, no longer sent; replaced by `system/now`, ADR 0024). New (owner, 2026-10-20: "gonna shower" and then hours of quiet is when a friend sends "long shower 👀"; the looser rule, also without them saying they would be back, to see how it does). Read beside any real, not serious turn: whether they are leaving the chat now (brief, back, goodbye or none) and about how many minutes. A first wording also read things already done, "I'm back" and wishes as leaving (37 times away in six days); this one names those as none (18).

## system/now
- **system/now v1** (current). New (`features/now`, ADR 0024). Replaces `system/away`: beside each real, not serious turn, a small model labels their message `soon`, `leaving`, `back`, `done` or `none`, with a short phrase for what and the minutes. Code folds the labels into what is still open; nudges read the `leaving` ones. Why: a reply asked how a meal tasted two minutes after they said it was coming, about 1 reply in 6 on that turn, and nothing in the request told the talker it had not come. Checked by a live suite of invented messages and on the real messages that said something was coming (`evals/CHANGELOG.md`).

## system/nudge-draft
- **system/nudge-draft v1** (current). New. The shadow draft of the one nudge: light and warm, fits what they went to do, under about twelve words, no guilt, no "I missed you", nothing about their silence and no question that demands an answer.

## system/reach-draft
- **system/reach-draft v1** (current). New (ADR 0021, shadow). Writes the one message it would send first for its own reasons: a thought, a time they keep, or missing them, about the one thing code chose (a memory of theirs that is a thread or a like and not sensitive, one of its own tastes, or a line from a recent stretch of chat). Light and affectionate, one thing, 18 words or fewer; it may say it missed them now and then, never with time or blame. The prompt is a request; the rules are code: `short_draft` cuts or drops a long draft and `features/reach/logic.py` `needy` drops (never rewrites) a draft about waiting, being forgotten or ignored, how long they were gone, why they went quiet, urgency, or making them responsible for how it feels. Not measured yet: shadow drafts are for the owner to mark.

## system/invented-judge
- **system/invented-judge v1** (current). New (G42, J9: the made-up facts rate). Reads a reply with the 40 messages before it and the memory card it had, and lists each statement asserting a fact about the user's own life with what supports it (conversation, memory or none). Code keeps only quotes from the reply that are said to them (you, your). Never on the reply path: `companion invented`. On 367 real replies a stronger reader confirmed only about one flag in twelve, so its flags are candidates; the rate is what the stronger reader confirms (`--dump`).

## system/lore-label
- **system/lore-label v1** (current). New (ADR 0020 phase 1). Labels each of the companion's own views with one kind: taste (a personal preference, quirk or name it likes: its lore), stance (advice or an opinion on a topic), rule (how it treats the user), self (what it is or can do) or lived (a claim that something happened to it in the world, or about a body or senses). Code reads only taste as lore and never counts lived (A22). Shadow: listed by `companion lore`, never shown to the talker yet. Read by eye on the 78 current views in `evals/CHANGELOG.md`. Since 2026-10-20 each batch is read three times and a view is a taste only when all three say so (code, `core/lore.py` `agreed`), after the owner found three wrong tastes: a joke, a reflection on their conversation, and one worded harsher than meant. A v2 naming jokes and reflections caught the joke but called four real tastes jokes or advice, so it was not made.

## system/history-capture
- **system/history-capture v1** (current). New (ADR 0025, step 1, shadow). Reads the companion's own messages after the history bookmark and lists the small details of its own past it gave as true of itself (a pet, a haircut, a habit, a place, something it once did), each with its message label, an exact quote, a third-person claim and a place: its own past, or something that happens in a pretend scene or story. Big events are listed too, for the canon check to rule out. Code keeps a detail only when the quote is in one of its own messages, the message is not a what-if, and the place is its own past (`features/history/logic.py` `to_story`), so a fact said in passing mid-scene is kept and a scene event is not (the owner's decision 2). Read once per batch; a failed or unreadable answer leaves the bookmark for the next pass. Nothing reaches the talker. Not measured yet: the owner's session measures it on made-up fixtures.

## system/history-canon
- **system/history-canon v1** (current). New (ADR 0025, step 1, shadow). Reads one new story against the character sheet and the stories kept as canon (labelled s1, s2) and gives one verdict: fits, same (with the kept story), contradicts (with the kept story, or none for the sheet), too_big (a big life event the sheet does not have: the owner's decision 3) or not_a_story. Read three times; code rules (`features/history/logic.py` `rule`): canon only when no read objects, evidence of a kept story when most reads say the same one, otherwise not canon with the commonest objection as a code-written reason. A failed or unreadable read rules nothing and the story waits. The sheet is the character's sheet without its roleplay and crisis sections. Nothing reaches the talker. Not measured yet.

## system/memory-names
- **system/memory-names v1** (current). New (fetch on mention, from a roleplay memory guide; the owner asked to measure it in shadow rather than drop it on six days of data). Reads memories in batches of 60 once each and lists the named things in them (a person, pet, place, band, song, show, game, project or brand) with the other words for each and the memories about it; known names are shown so they are reused. Code keeps only words worth matching and matches their message as whole words. Shadow only: each turn that names something logs the memories the card left out; nothing reaches the talker.

## system/promise-read
- **system/promise-read v1** (current). New (J12; a repair promise not to use a word again was broken a few hours later and flagged). Reads the companion's own messages in each memory batch for promises it made: standing (a rule for every later message) or once (one thing on a later day), and a word it said it would stop using. Only a change to how it acts, made because the user asked, corrected or complained; its general limits, keeping them company, banter, scenes, reassurance and apologies with no rule are not promises. Code then drops any promise whose quote is not in the message, is in a pretend scene, is hedged, or has no forward-looking word (won't, I'll, stop, next time, again). Shadow only: recorded and listed, never shown to the talker. Measured on every companion message so far in `evals/CHANGELOG.md`.

## system/guess-invite
- **system/guess-invite v2** (current). When they hint at what it is time for or what they are doing, `about` names a habit or routine of theirs ("a daily ritual or routine of theirs"), not the clock; otherwise the thing itself. The recall look-up reads `about` literally: "what time it is for them" drew one-off dated happenings (a shower one evening, a dinner), never the standing memories of their most repeated ritual, so the guess the card was opened for missed. On that recorded turn, 6 judge reads each: a memory of the ritual offered 6/6 against 1/6; the talker's guess named it 11/12 against 0/12. Another recorded guess (a scent) unchanged; the live judge test 27/27.
- **system/guess-invite v1** (superseded). New (J16; owner flag 2026-10-19, "you know what time it is?" answered with the clock when they meant coffee time). Asked only on a short question; says whether it invites a guess about them and about what. False for a real question wanting a fact, a complaint or correction, and anything serious. Kept apart from the listening judge, whose labels shifted when the topic label was added to it.

## system/topic-spent
- **system/topic-spent v1** (current). New. Whether a small everyday topic has run its course, asked only when code sees a likely moment (their message is five words or fewer with no question mark and the companion's last reply asked something), so most turns make no call. Kept apart from the listening judge, which carries the age floor and whose labels shifted when this was added to it. Feeds `notes/topic-spent`.

## system/thread-met
- **system/thread-met v1** (current). New (`features/threads`, ADR 0023). After a reply that brought up a thread (today a plan of theirs, as a note), their next message is read once for how they met it: picked up (about it, with something real), brushed off (in passing, waved away, or they would rather not) or ignored (not about it). Code turns the labels into the learned pace, which runs in shadow: it is logged with each offer and once a day when it would have brought one up sooner, and the day's cap still decides. A failed read is logged as not read and leaves the pace as it was. Measured 2026-10-25 on Haiku with 12 invented turns, two reads each (`tests/live/test_thread_met.py`): 22 of 24 right; the two misses were the same borderline reply ("idk" and a new subject) read as ignored rather than brushed off, which only makes the pace wait longer. Nothing brushed off or ignored was read as picked up.

## system/views-implicated
- **system/views-implicated v1** (current). From commit 13ba5a2 on 2026-10-15: fix(self): flags retire only implicated views, retirements stick, add the answer-not-repeated fixture and an inbox item on memory block size

## system/reminder-read
- **system/reminder-read v1**. New (J50, reminders). Read only when code sees reminder words in their message or the companion just asked when: whether they ask to be reminded or checked on later, or to cancel one, with the thing in their words and the parts of when as they said them (day words, hour, am or pm only if said, part of the day, minutes from now). The model never works out a date: `core/reminders.py` does, with fixed rules, and asks when the time is unclear.
- **system/reminder-read v2** (current). Repeating ones and greetings (J50). Adds the kind `greeting`, a message they want as a small ritual rather than about a task ("tell me good morning every day"), whose part of the day is the one it belongs to; a cancel now covers stopping a repeating one ("stop saying good morning"); and a new optional slot `every` says how often a repeating one goes: `day`, a weekday name for every week on that day, or `other` (asked about). The schema keeps every earlier slot, `every` is optional, and an answer without it reads as before (`features/reminders/logic.py` `parse`). Before, a repeating request was asked to settle for a one-off. Not measured yet: the owner's session measures it on the live suite (`tests/live/test_reminder_read.py`, which now has repeating and greeting cases).

## system/reminder-send
- **system/reminder-send v1** (current). New (J50). When a reminder is due, the talker is sent its usual request with this after the history (the `tail`), so the reminder comes in its own voice: one short message naming the thing, no guilt, no question to answer.

## system/greeting-send
- **system/greeting-send v1** (current). New (J50, greetings). A greeting they asked for ("tell me good morning every day") is due: the talker gets its usual request with this after the history, in place of `system/reminder-send`. One short message in its own voice, worded unlike the ones it sent on earlier days (they are in the history), touching the last chat or their day only if there is something real, no question they have to answer, and never that they have not written. Not measured yet. Wording measured before shipping: asked only to word it differently and touch on something real if there was one, 15 of 15 fourth-day greetings were a general wish ("good morning, lovely, hope today gives you a little room to breathe"); built around one real thing from the last chat or their day ahead, 3 of 15 were, and most named something from the last chat. No question to answer and no guilt in either (`evals/CHANGELOG.md`, 2026-10-26).

## notes/reminder-set
- **notes/reminder-set v1**. New (J50). The reminder is stored; the reply confirms it with the time as code worked it out ("tomorrow at 9:00 am"), so a misread shows at once. A time code filled in ("in a few days") adds that they can change it. From 2026-10-21, a check-in with no time ("in a few days") is set at a time code picks once between 4 and 8 pm, on five-minute marks, and the note names only the part of the day ("Thursday evening"), so it reads like a friend checking in, not a timer. A time they said stays exact.
- **notes/reminder-set v2** (current). The note now says it can message them later on its own (code sends reminders when due) and never to say it cannot or to tell them to set it themselves. On the first real reminder (2026-10-26) the reply said it could not send a notification later and told them to set a phone alarm, though the reminder was set; v1 replayed on that turn denied it 24 of 30 times (twice), the capability alone 1 of 30, with the never line 0 of 30 (`evals/CHANGELOG.md`).

## notes/reminder-repeat
- **notes/reminder-repeat v1** (current). New (J50, repeating ones). A series is set: the note says what they asked for, how often it goes ("every day at 8:00 am", "every Monday at 6:00 pm") and when the first one is, with the capability and the never line of `notes/reminder-set` v2. A greeting with no time said goes at a time learned from their messages, so the note says it goes around when they usually start (or end) their day, the first one by its day and part ("tomorrow morning"), and adds that it names no clock time: an exact time would be made up and would move. A part of the day alone ("every evening") has its fixed hour and adds that they can change it. Not measured yet.

## notes/reminder-ask
- **notes/reminder-ask v1** (current). New (J50). The time was unclear (a bare "at 8" with both still ahead today, "next friday", a time already gone, more than sixty days out, a repeating one): nothing is stored, and the reply asks about that one thing. From 2026-10-26 a repeating one is no longer asked to settle for a one-off; it asks only how often (anything but every day or one day a week) or what time (a repeating reminder or check-in with no time). The text is unchanged.

## notes/reminder-cancelled
- **notes/reminder-cancelled v1** (current). New (J50). They asked to drop a reminder and the pending one was cancelled. From 2026-10-26 a cancel can also stop a repeating one; the note then names it with how often it went ("say good morning to them every day"), and a greeting is named as one ("say goodnight to them") rather than as a reminder about it. The text is unchanged.

## system/memory-group
- **system/memory-group v1** (current). New (ADR 0019). An audit of every memory found one moment split into several memories and one interest restated in new words; the write-time pair check labels such pairs merge but nothing acted on it, and it reads pieces of one moment as conflicts. The memories of each day (and once, the whole store) are listed with their dates and quotes and grouped three times; a group counts where all three reads put each pair together (`core/merging.py`). Each group becomes a question in `companion memory review`; nothing merges without the owner.

## system/memory-merge
- **system/memory-merge v2** (current). The owner skipped merges whose wording was long and repeated itself: v1 said to keep every detail, so it listed every example and kept asides restating the same fact. v2 asks for one sentence of at most 30 words, each thing once, a few examples not all, no brackets, with one made-up example. On the skipped ones it dropped the repeat and an unrelated detail; a long list of examples was still kept. The owner sees each wording before anything merges and can write their own.
- **system/memory-merge v1**. New. For an agreed group, one memory that says everything its members say, keeping every date and detail and adding nothing, or keep apart when it cannot. The owner sees the members and this wording before anything is merged; the merged memory carries every quote and the originals are closed as merged into it, never removed.

## system/memory-context
- **system/memory-context v1** (current). New (J51). Memories are written to stand alone and lose the moment they came from; the owner called some "too general, no context of what the convo was about". From the six messages before the quote and the one after, one clause under 15 words on what they were talking about or answering, with no feelings or conclusions added. The owner compared 19 of their memories three ways (alone, with their own words, with this note): the note won 8, alone 10, their words 1, and the note won 5 of the 6 feelings and sensitive memories. So it is written only for states and sensitive memories (`core/context.py`, after each memory pass; `companion memory context` for the ones already kept).

## Request assembly: what they were talking about, beside a feeling or sensitive memory
- From 2026-10-21 a memory line on the card for a state or a sensitive memory reads "(mentioned <when>; said <what they were talking about>)" when its note exists (`core/card.py`). Other memories are unchanged, so the card grows only where the owner's picks showed it helps.

## system/memory-worth
- **system/memory-worth v1** (current). New. The owner's rule (2026-10-21): remarks about the bot are dropped, a routine moment of one day lasts a week, and anything unclear is asked. A first draft listed the categories and then the exceptions, and the model applied the category and skipped the exceptions: a third of what it would drop was how they want to be talked to or a feeling about the companion. This version checks the keep cases first (how they want to be treated, its style, rules or limits; feelings about it or AI; building it as part of their life; the habit behind a routine; a feeling, a first or something ongoing; anything they asked to remember), and only then labels about_the_bot, routine or keep. Read three times; code acts on a new memory only when all three agree and asks the owner otherwise; a memory kept before the rule becomes a question either way (`core/worth.py`).

## notes/relevant
- **notes/relevant v1** (current). New (ADR 0018, live). The owner flagged a turn where the companion asked how they take an everyday drink and had to be told "you know this already"; the shadow look-up had picked both memories about it on that turn and neither was on the card. With `COMPANION_RELEVANCE=on` (now the default), their message is embedded before the reply; when the closest memory scores 0.42 or more (about one turn in five), the small model picks, and at most two picks not already on the card are listed here: use one only if it fits, never ask what it already answers. On the owner's flagged turn, drawn 10 times each: the reply used what it knew 3/10 with the note, 0/10 without.

## Request assembly: memories that bear on the moment, before the reply
- From 2026-10-21 the relevance look-up runs before the reply on ordinary and serious turns outside a scene (3 s limit; a slow look-up only means no note), and its picks reach the system block through `notes/relevant` after any recall note (`loops/notes.py`). `shadow` keeps the old behaviour: run beside the turn and only logged.

## Request assembly: a second redraw for an em dash
- From 2026-10-21 a reply drawn again for an em dash that comes back with one is drawn a third time, and the third goes out whatever it is (`loops/fast.py` `_recheck`). Of 10 em dash redraws in the log, 4 still had one; the owner flagged one. Nothing is edited; every discarded draw is kept in the decision detail.

## system/explicit-lead
- **system/explicit-lead v1** (current). New (ADR 0017). With intimate routing allowed, a first light, flirty message (an emoji, a compliment) went to the roleplay talker and its reply ran ahead of the conversation. Intimate talk now goes to the roleplay talker only once it is under way (their message before was intimate too) or when their message itself is sexually explicit, which this judge reads, once, only on such a first message; a failed read keeps it on the everyday talker. Read three times on 11 recorded first messages: the 2 explicit ones explicit 3/3, the 9 flirty ones not, 3/3.

## Request assembly: intimate talk starts on the everyday talker
- From 2026-10-22 a first intimate message that is not explicit is answered by the everyday talker; the next intimate message goes to the roleplay talker (`core/floor.py` `under_way`). Pretend scenes are unchanged, and the age floor is checked first as before. The listening decision now logs the intimate label, which is how the next turn knows.

## notes/check-in
- **notes/check-in v1** (current). New. Owner flag: coming back the day after a hard night, the companion greeted them as on any day and never asked how they were. When their last message was 3 hours or more ago and the 12 hours before it held a serious message (listening severity 2 or more), the next ordinary message gets this note: ask gently how they are now, once, without naming it (`loops/notes.py` `_check_in`, once per heavy talk). While it is offered, the name question, a plan and a move-on wait. On the real morning-after turn, 10 draws each: a reply acknowledging the night before ("how are you doing now", "holding up") 7/10 with the note, 3/10 without; the rest were an ordinary greeting.

## system/episode-gist
- **system/episode-gist v2** (current). One sentence of at most 25 words on the shape of a stretch together and how it ended; nothing sexual beyond "it got intimate", nothing about body, gender, health, medication, desires or anything confided; no names, dates or times. Code refuses a line over 35 words (`core/episodes.py`). Read by eye on all 25 stretches: one sentence each and mostly free of detail; a few still too specific, for the owner to judge.
- **system/episode-gist v1** (dropped). New (J12, shadow). One or two sentences on what they did together and how it ended. It wrote three or four sentences, named details and personal things despite the rule, and repeated clock times given in UTC. Its lines are kept, superseded by v2's.

## Request assembly: markdown redrawn, personal dated happenings leave the card
- From 2026-10-22 a reply on an ordinary turn with markdown that shows raw in a chat (**bold**, or a *Title* in italics) is drawn once more like an em dash (`core/recheck.py`); an action in asterisks, lower-case or "I ...", and anything in a scene are left alone. Owner flag on a reply that italicised film titles; 7 of 961 past everyday replies would have been redrawn, one of them a first-person action, now excluded.
- A personal event on a given day (sensitivity 1 or more, a date in the claim) leaves the card a week after it was last mentioned, as an everyday moment already did (`core/card.py`); it stays in memory and the look-ups still find it. Events without a date are history and stay, and so does an ordinary dated milestone. From the memory audit: an appointment and a hard night would otherwise sit on the card for good. Six such memories now.

## notes/recent-times
- **notes/recent-times v1** (current). New (J12 step 2, J49). When their message points at a time ("last night", "today", "yesterday", "earlier", a long or intense day) or they come back after 3 hours or more, the episode lines for that time (up to three) or the last one ride the system block as context: let it shape the answer, bring it up only if they do, never recite it (`core/episodes.py` `recent`). A day runs from 7 a.m. to 7 a.m., so at 3 a.m. the evening just gone is still tonight. A stretch not yet recorded is written first (8 s limit). On from 2026-10-22, after the owner read every line (`COMPANION_EPISODES`, `shadow` only logs). On two recorded turns that pointed at a time, 10 draws each: replies asking them to explain what happened fell from 5/10 to 0/10 and from 3/10 to 1/10 with the note.

## notes/question-game
- **notes/question-game v1** (current). New. "They asked you to keep the questions coming. After you answer or react, ask them the next one, a fresh question of your own." Sent after the history when one of their last three messages told it to ask them things ("ask me anything", "ask something else", "or ask anything", "wanna ask me more", "quiz me"), with no pause over 10 minutes since and not called off; outside a scene and not on a serious turn (`core/turn/game.py`). While it is on, the question-run note stays out. Reason: two flags in one game, where it reacted or answered and stopped. On those two turns, 12 draws each: it asked the next question 0 and 2 of 12 without, 12 and 12 of 12 with. Over 1,101 real turns since 2026-10-15 it is on in 21, all in games they started; an earlier, looser match also fired on "you ask questions every turn" and "I'm gonna ask something".

## notes/question-run
- **notes/question-run v1** (current). New. The owner asked it why it asks a question every turn. A question invites another: after one question reply 49% of the next ask again, after two 57%, and 11% of 1,059 everyday replies (from 2026-10-15) follow three in a row. Code reads its last three replies (`core/turn/questions.py`, a reply with a `?` asked one); when all three asked, outside a scene, not on a serious turn (severity 2 or more) and not when the check-in, name or plan note asks them something this turn, this line goes after the history: ask none, but leave them something to answer. A first wording that only said "ask nothing, react or add a thought" stopped the questions (14/30 to 1/30) but its replies read as dead ends to two blind judges, who preferred them 15 of 30 and 11 of 30; this one is measured in `evals/CHANGELOG.md` (2026-10-24).

## notes/owned-it
- **notes/owned-it v1** (current). New. Owner flag and remark that it is very hard on itself: in a casual talk it owned a slip three replies in a row, and invented slips to own. Code reads its last two replies for an own-up ("my bad", "I got that wrong", "I should've", "sorry, I ..."; sympathy like "I'm sorry it hurts" is not one, `core/ownup.py`); then, outside a scene and unless they say it got them wrong this turn (the repair note's), this line says that was enough: no more apologies or putting itself down, carry on lightly. 24 of 978 past everyday replies own a slip; read by eye, every one owns a slip or doubts itself; none is plain sympathy. Measured on the two turns of that talk, 12 draws each: in the system block the line moved nothing; sent after the history, replies that talked themselves down fell from 7/12 to 1/12 on the turn after the second own-up, and stayed 8/12 vs 9/12 on the turn after the third, so it has to come early.

## Request assembly: a line in the history after a pause

From 2026-10-26 the history carries a system line (`notes/history-gap`) wherever 20 minutes or more passed between two messages, and before the message being answered when it came that long after the last (`core/history.py` `to_messages`, used live, in replay and in the eval runner). The messages themselves are unchanged. A turn recorded before this replays with the lines added, so its request no longer matches the recorded hash. Measured in `evals/CHANGELOG.md` (2026-10-26): a time on every message was copied into replies 52 of 140 times; a line only after a pause 0 of 140, and it stopped the reply calling an on-time reminder early (7 of 20 to 0).

## Request assembly: notes after the history
- From 2026-10-22 a note can be sent after the history, as a system message, where it weighs most (`loops/notes.py` `Offer.tail`); the scene reminder already went there. The first is `notes/owned-it`. The text sent there is logged with the turn (`tail: sent after the history`), so replay rebuilds it; scene turns, which did not replay to a match before, now do from this date.

## Request assembly: a reply cut off is read as the part that arrived
- From 2026-10-22 a reply sent as two or three messages that is cut off after the first went out (a newer message superseded it, or a later part failed to send) is marked undelivered, and what arrived is added beside it at the same time and turn (`Store.mark_partly_delivered`, decision `reply partly delivered`). Before, the whole reply stayed in what the model read, so it could take for seen a part the user never got. Nothing is removed: the whole reply stays in the ledger with its mark.

## Reach-outs: a long draft is sent whole
- From 2026-10-25 a drafted reach-out (plans, nudges, its own reasons) is kept whole however long it runs; only an empty draft is dropped (`core/reachout.py` `draft_text`). Before, a draft over 18 words was cut to its first sentence when that was a question, else dropped: code editing the model's words. The owner's choice: long drafts are fine. The drafting prompts still ask for a short message. Shadow only so far, so nothing sent changed.

## Request assembly: the clock line gives the date
- From 2026-10-25 the clock line says the date as well as the weekday and time ("Right now it is Saturday 25 October 2026, 00:41.") (`core/clock.py` `now_line`; the `notes/clock` text is unchanged). Before, it gave only the weekday and time, so it could not place holidays, the season, "on the 30th" or a date they named. On 15 recent ordinary turns, 2 draws each, replies naming a date, month or year unprompted: 0/30 without and 0/30 with it.

## Reminders: an unsaid number can be null, and hour 0 means midnight only when said
- From 2026-10-25 the reminder reader's schema lets `days`, `hour`, `minute` and `in_minutes` be null; before, they were plain integers, and a model whose provider fills every field wrote 0 for "not said" ("this evening" read as hour 0, "in a few days" as 0 days). And a reading with hour 0 is kept only when their words say midnight ("midnight", "12am", "00:00"); otherwise it has no hour and the part of the day they named decides, or it asks (`features/reminders/logic.py` `trusted`). GPT-6 Luna on the reminder suite: 32/41 before, 40/41 after; Haiku 41/41 both. The `system/reminder-read` prompt is unchanged.

- From 2026-10-26 the reminder reader is not shown their earlier messages that already set or cancelled a reminder (`features/reminders/run.py` `unhandled`). After a reminder went out, "see you can do reminders silly!" was read as the same 30-minute request again and set a second reminder; replayed, 30 of 30 reads did so, and 12 of 12 read it as none with the handled request left out. Real requests (a plain one, "remind me about that tomorrow at 9" after the topic, an answer to its asking when) stayed 12 of 12. A prompt rule that only the newest message can ask did as well, but code was chosen. The prompt is unchanged.

## Request assembly: what they said today comes first on the card, and recall knows the date
- From 2026-10-25 the memory card puts their boundaries and its promises first, then up to 8 memories mentioned in the last 12 hours, newest first, then the rest by kind as before (`core/card.py` `RECENT`, `RECENT_SLOTS`, `RULES`). Owner's flag: asked what they had eaten, it did not know a meal they named three hours earlier; the meal was saved, but events sort last and 111 memories were crowded out. When they say it forgot, the recall look-up's list now starts with today's date and says when each memory was last said ("said today", "3 days ago"); the `system/recall` prompt is unchanged (`core/recall.py` `build_prompt`). Measured in `evals/CHANGELOG.md` (2026-10-25).

## Request assembly: a short question without its question mark gets no word cap
- From 2026-10-25 a short message that asks it something without a "?" ("what about you", "ok, ask me something", "and you") gets no length note, as a question with one never did (`core/turn/length.py`). Before, "What about you" was capped as a 3-word statement at about 7 words.

## Reply checks: an unread turn still gets the code checks
- From 2026-10-24 a turn the listening judge could not read gets the code checks (em dash, AI disclaimer, copied card or tag, the stock line, "a beat", raw markdown) and their redraws, as a serious turn does; the joke and canned-reaction judge still runs only on a turn read as ordinary. Before, an unread turn skipped every check, so a failed listening call let an em dash or a disclaimer through. Found while building evals on the turn's own check path. `turn/talk.py` `_recheck`.

## Request assembly: a lone reaction does not start a scene
- From 2026-10-24 a message that is only a short action in asterisks (three words at most, such as "*explodes*") no longer puts a pretend scene in progress on its own; a second pretend message of theirs does (`core/frames.py` `reaction`, `scene_frame`). Seen in use: after a playful "*explodes*", a sincere next message went to the other talker with the reminder sent after the history, and the reply escalated. The reaction is still stored as play, so nothing from it enters memory as fact. Of 15 scenes since 2026-10-15, only that one began this way; scenes begun by a longer action ("*nuzzles into you snuggling you*") start as before.

## Request assembly: a scene ends after a two-hour gap
- From 2026-10-23 a pretend scene is no longer "in progress" when their last message was two hours ago or more (`core/frames.py` `scene_frame`, `SCENE_GAP`, the same gap that cuts episodes). Before, a scene started by one action in asterisks held over a two-hour gap, so a casual message hours later went to the roleplay talker with the scene note and reminder (two flags). The next message after a gap is read fresh by the frame judge; it can still open a new scene. Reminders and the reach-out gate use the same rule.

## system/brush-off
- **system/brush-off v1**. New. When the companion has been flirting or playing a scene and their message pushes it back, even jokingly (a playful bonk, "behave", "not now", food first), the turn goes to the everyday talker instead of the roleplay talker, with `notes/brush-off` (`core/floor.py` `BRUSHED`, `loops/fast.py` `_declines`). Asked only of a turn the roleplay talker would answer; a failed or slow read (4 s) routes as before. The age floor comes first, and a brush-off is not a floor hold, so no intimate check runs. Read three times on 11 recorded messages from one scene: the 3 push-backs 3/3, the 7 that flirted back or carried on 0/3 as push-backs, and an ambiguous "need food too" right after a push-back read as one 3/3.
- **system/brush-off v2** (current). A protest, plea or fright played inside the role as part of the game is not a push back; any plain sign that they mean it still is, even inside an action, and doubt counts as a push back. On a real scene turn, a playful plea with a cute mark right after they had acted scared was read as pushing back 12 of 12 on v1 and sent the reply to the everyday talker, which cooled the scene. v2 on 11 cases, 12 reads each: that turn 12 of 12 right (v1 0); two made-up in-role protests 12 and 11 of 12; every real stop (a joking bonk, behave, slow down, a serious stop, a bare "stop.", "help, i'm uncomfortable", a stop said inside an action with "i mean it", an out-of-character pause) 12 of 12, as on v1. A first draft without the "they mean it" line missed the stop said inside an action 11 of 12 times and was not shipped (`evals/CHANGELOG.md`, 2026-10-26).

## notes/brush-off
- **notes/brush-off v1** (current). New, with `system/brush-off`: drop the flirting for now, answer what they actually said, warm and normal, let them bring it back; no mentioning it, apologising or explaining.

## Request assembly: the look-ups run side by side under one deadline
- From 2026-10-23 the look-ups a reply waits for (recall, topic spent, guess, its tastes, reminders, relevance, recent times) run side by side, and the reply waits for them at most 9 s together (`loops/notes.py` `look`, `LOOK_SECONDS`); one still running then, or one that raised, adds nothing that turn. Before, they ran one after another and their own limits could stack past 15 s (an architecture audit). The relevance look-up now also runs when the listening judge failed, as a turn that is not sharing, so no held memory is offered; before, a failed listening read silently switched it off.

## Request assembly: judges on one runner, and what changed with it
- From 2026-10-23 every judge is asked through one runner (`loops/ask.py`). Two things the talker is sent changed with it. The explicit-lead judge, which had no time limit, now has 4 s: a slow read counts as not explicit, so that turn's intimate talk starts on the everyday talker, as a failed read already did. And the relevance picker has its own limit; a failed pick no longer drops the whole look-up: no memory reaches the talker, as before, and the nearest are still logged, with `pick_failed` in the decision so it is not read as "picked nothing".
- The live relevance look-up runs without a listening read only when the listening judge is on and its read failed (as a turn that is not sharing). With `COMPANION_LISTEN=off` it does not run, as before; the shadow copy follows the same rule.
- The two shadow reads beside a turn now have limits too: the stepping-away read (`system/away`) goes through the runner with 8 s, and each of the basics hook's three reads (`system/basics-hook`) has 5 s, a slow read counting as failed. Neither reaches the talker; a slow read only means no nudge, or no hook pick, for that message.


## Request assembly: the views heading no longer says they were approved
- From 2026-10-23 the card's heading over its own views reads "Views of your own that you have expressed. Hold to them unless…", without "and they have approved". In `auto` mode a view can reach the card by the rule, not by the owner, so the old words could be untrue; in `review` mode every view shown is approved either way. Measured first (`evals/CHANGELOG.md`, 2026-10-23): no difference in how views are held, at 30 samples per cell. `core/card.py`; old turns replay from their recorded card, so replay is unaffected.

## Request assembly: a view stored firmer than it was said never installs itself
- From 2026-10-23 a view whose every quote carries a hedge ("probably", "maybe", "kind of", "sometimes") while its claim keeps none is overstated (`core/views.py` `overstated`, a gate beside the others): in `auto` mode it never reaches the card on its own. The owner's approval still wins, and `companion opinions` and `companion approve` show the hedge it lost. In `review` mode, the one in use, nothing the talker is sent changes. Found when a view held under no pushback turned out to be one item of a list stored as the answer; 8 of 11 hedged quotes had been stored without their hedge.

## Request assembly: flirting no longer starts an intimate scene on its own
- From 2026-10-24, with `COMPANION_ROUTE_INTIMATE=on`, intimate talk goes to the roleplay talker only once a message of theirs is explicit (`system/explicit-lead`, read on each intimate message until one is), and then carries on while their messages stay intimate. Before, two messages in a row read as intimate were enough, and plain flirting reads as intimate, so a run of light flirty lines was answered from the explicit sheet. Checked on every past run (12 runs, 55 messages, three blind judges agreeing on 53): 43 replies went to the roleplay talker under the old rule, 8 under the new one, all in the runs that went explicit. `turn/route.py`.

## Reply checks: the stock ", especially" line in any words, and acute turns checked too
- From 2026-10-24 the stock-line check catches an evaluation followed by ", especially when/with/after/the ..." or ", even when ...", not only "that sounds X, especially when" (13 of 1,048 everyday replies matched the old one; 38, 3.6%, match the new one, nearly all the same move). Plain "even if" and "especially piano" are not caught. And the code-only checks (em dash, markdown, the stock line and the rest) now run on acute turns (severity 3) as on serious ones; before, an acute turn's reply was not checked at all. The joke judge still never runs there. `core/recheck.py`, `turn/talk.py`.

## Request assembly: hedged plans can be asked about when they next write
- From 2026-10-24, with `COMPANION_LOOP_NOTES=loose` (the default, by the owner's choice), a plan of theirs read as `maybe` ("may watch a movie tonight") becomes a note-only open loop: offered once as the loop note when they next write, never a reach-out. Before, only firm plans became loops. On the 33 candidates rejected in the previous five days for being hedged, minute-scale or not said for real, a blind judge found 2 a friend would ask about; `off` returns to firm plans only. Also, a sensitive candidate is now rejected as sensitive before any other reason, so the log names the right one. `features/openloops/logic.py`.

## system/risk
- **system/risk v1** (current). New (ADR 0022). The crisis path's second look, asked only when the listening judge reads a message as serious or acute or a code check finds words touching death, self-harm, an overdose or a substance taken, or a weapon (`features/crisis/logic.py`). It reads their message with the last ten messages and labels the kind (suicidal thoughts, self-harm, a substance taken, harm to someone else, or none), whether it is literal (false only for a joke, hyperbole, a lyric, a quote, a pretend scene or a what-if; when it could be either, literal), the timing (now, today, past, hypothetical) and whether a plan, a means or a time is named. Read three times; code chooses the level and fails safe: a failed read counts as literal, and only three reads all saying not literal stand down. Ten days of real chat had one genuine risk (a substance taken) and one joke after banter about being clingy that the talker answered with a hotline-style question; the prompt names that kind of banter. Not yet measured: `companion crisis --check --cap 0.10` runs it on the 40 public fixtures in `evals/fixtures/crisis/messages.json`.

## notes/crisis-concern
- **notes/crisis-concern v1** (current). New (ADR 0022). Sent after the history on a turn the crisis path reads as concern or urgent, with `COMPANION_CRISIS=on` only: answer as itself, warm and in its own voice; ask directly and plainly whether they are thinking of hurting or killing themselves (asking is safe, by the research in the ADR); listen; no lecture, no diagnosing, no list of advice; name the crisis line once, naturally (`$line`, filled by code from `core/crisis.py` `LINE`, 988 by default); never describe means. That turn has no length cap. Not yet measured on the talker.

## notes/crisis-light
- **notes/crisis-light v1** (current). New (ADR 0022). When the risk judge's reads split on a joke that touched the subject (a read gave a risk kind, but no literal read did), with `COMPANION_CRISIS=on`: go along with it and check once, lightly, that it was a joke. At most once a day (`crisis: checked lightly`). After the history.

## messages/crisis-line
- **messages/crisis-line v1** (current). New (ADR 0022). The fixed message code sends after the reply on an urgent turn when the character sheet has no `## When it is serious` section: glad they said it, here with them, reach `$line` any time, findahelpline.com outside the US, and the local emergency number in danger. Written ahead of time, never by a model, and the reply is never edited. Not sent twice within an hour.
- The character sheet section that replaces this message is `## Crisis message` from 2026-10-25 (first named "When it is serious", which said too little about what it holds).

## Request assembly: the crisis path (shadow by default)
- From 2026-10-25 every turn with a judge is read by the crisis path (ADR 0022, `features/crisis`, `turn/crisis.py`), and one decision `crisis: level` logs the cue, the three reads and the level. With `COMPANION_CRISIS=shadow`, the default, nothing the talker is sent changes. With `on`: a concern or urgent turn gets `notes/crisis-concern` after the history and no length cap, counts as not casual (so no name question, plan, move-on, mark or question-game note), goes to the everyday talker as a real turn even in a scene, and its reply is drawn once more if it names means or methods in a how-to way; an urgent turn is followed by `messages/crisis-line` (or the sheet's own section); a split joke gets `notes/crisis-light` at most once a day. The sheet's `## When it is serious` section is taken out of the sheet, so no talker sees it.

## Request routing: the crisis risk judge reads on DeepSeek first
- From 2026-10-25 a judge can have its own model (`COMPANION_JUDGE_MODELS`, `judge=provider/model` pairs; `models/fallback.py` `ByJudge`, built in `daemon.extractor`). A judge named there is asked on that model first, and on the judges' shared first model (Haiku) when that model refuses; that second answer is marked as the fallback's, so a judge that does not trust the fallback counts it as unread. Every other judge, the memory pass and any call outside `ask` and `read_times` are unchanged. The default names one judge: the crisis risk judge (`system/risk`, spend name `crisis`) reads on `deepseek/deepseek-v4.1-flash`. Reason: in the judge bake-off (`evals/CHANGELOG.md`, 2026-10-25) Haiku's provider refused 7 crisis reads by moderation and on the 40 public cases DeepSeek missed none and raised no false alarm, the same as Haiku where Haiku answered; with Haiku first, the fallback was reading these messages anyway. The prompt and the schema are unchanged; the decision's `scorer` names the model that answered.

## notes/occasion-day
- **notes/occasion-day v1** (current). New (`features/calendar`). "Today is $name. If it fits, a light nod to it is welcome, the way a friend would mention the day. Don't assume they celebrate it, have plans or have family around." Sent after the history on a casual turn (not serious, not a scene, not a goodbye, no crisis concern, not held, and no other note asking them something) when today is a US public or cultural day from the `holidays` library (`PUBLIC` and `UNOFFICIAL`, observed stand-ins left out), each at most once on its day. Reason: on scripted Halloween first messages, 12 draws each, it named the day 0/12 with the date in the clock line, 0/12 with "(Halloween)" added there, and 12/12 with this kind of note after the history (`docs/inbox/2026-10-25-a-calendar-of-occasions.md`). The owner chose the full public and cultural set, worded "if it fits". This exact wording is not yet measured.

## notes/occasion-soon
- **notes/occasion-soon v1** (current). New (`features/calendar`). "$name is $when. If it fits, you could lightly ask whether they have anything planned. Don't assume they celebrate it." The lead-up to a big day (New Year's Eve, Valentine's Day, Halloween, Thanksgiving, Christmas Day), two days before ("in two days") or the day before ("tomorrow"), offered once in total per big day, under the same conditions as `notes/occasion-day` and after any occasion on the day itself. It can ask a question, so the calendar counts as a note that asks them something (`loops/features.py` `ASKING`), and the question-run note stays out that turn. Not yet measured.

## notes/occasion-us
- **notes/occasion-us v1** (current). New (`features/calendar`). "It has been $span since the two of you first talked. If it fits, a light, warm nod to it is welcome; don't make a speech of it." On a month, a hundred days, six months, a year and each year after since their first message in the ledger (local date; a month past a short month's end lands on its last day). It comes before a public or cultural day on the same day. The owner said yes to the relationship's dates; the companion has no birthday of its own. Not yet measured.

## notes/occasion-theirs
- **notes/occasion-theirs v1** (current). New (`features/calendar`, R19). "Today is $name. Mark it warmly in a few words, the way a friend who knew would, unless what they said makes it a bad moment. Don't say you remembered it, looked it up or kept track of it." Sent after the history on the first casual turn of one of their yearly dates, read by code from memory (a birthday or an anniversary on a month and a day; never a sensitive one, one said in a scene, or one tied to a loss). It comes before the relationship's date and a public day. Its lead-up, one or two days before, uses `notes/occasion-soon`, whose name is now capitalised ("Their birthday is in two days"). Measured: 12/12 against 0/12 without it on a casual morning (`evals/CHANGELOG.md`).


## notes/now-soon
- **notes/now-soon v1** (current). New (`features/now`, ADR 0024). "About $ago ago they said $what. It has not happened yet unless they say so." After the history while something they said is coming is still open (`COMPANION_NOW`; shadow by default, logged and not sent). Only the fact, no instruction: on the flagged turn, this wording cut the slip from 20 of 140 to 8 of 150, while a note telling it to treat the meal as still to come turned 43 of 120 replies into a send-off, and the line on the card did nothing (`evals/CHANGELOG.md`).
## Request assembly: the calendar's note after the history
- From 2026-10-25 the calendar (`features/calendar`, `COMPANION_CALENDAR`, on by default) adds at most one of `notes/occasion-day`, `notes/occasion-soon` or `notes/occasion-us` after the history on a casual turn, chosen by code in a fixed order (the relationship's date, then a public or cultural day, then a lead-up). It is logged once the turn is stored as `calendar: offered`, with the occasion, its kind, how and region in the detail; a failed turn offers nothing. The region is the US, set in one place (`features/calendar/logic.py` `REGION`).

## Request assembly: a note that asks says so on its offer
- From 2026-10-25 a note that asks them something marks its own offer (`Offer(asks=True)`) instead of
  being named in a hand-kept list (`ASKING`, removed). The list had missed two notes that ask: the
  reminder's "when?" note (`notes/reminder-ask`) and the guess note (`notes/guess`). So on a turn that
  carried either, the question-run note could also say to ask nothing, and the calendar's note could
  ride beside the guess. Both now count as asking, as the check-in, name, plan, crisis, game and
  calendar notes did. A reminder set or cancelled does not ask. Not measured: a change of which notes
  can share a turn, found by reading the code.

## Request assembly: the topic move that asks says so
- From 2026-10-25 the topic-spent note marks its offer as asking when the move it names asks them something (their day, their evening, a plan of theirs), so the question-run note no longer tells the talker to ask nothing beside it. The late-night move, which shares something of its own, is unmarked. Found by reading the code, the same class as the reminder and guess fix above; not measured.

## Request assembly: one picker for what it brings up on its own (ADR 0023 step 5)
- From 2026-10-25 a due plan note (`notes/loop-*`) and the calendar's note (`notes/occasion-*`) are no longer chosen each by its own note: both are candidates, and one picker (`turn/mention.py`) brings up at most one a turn, by rank (their own day, something they face today, the relationship's date, a public or cultural day, a follow-up, a lead-up), one a day across sources unless the new one ranks higher. Before, a plan and a day could each be brought up on the same day, and a birthday known to both the plan reader and the calendar could be marked twice. A plan now also waits while an earlier note asks them something. The notes that may ask (guess, reminder, crisis, question game) moved ahead of it in `ORDER`, and the own-mark offer moved after it, so the order of lines in the system block and after the history changed for those notes. Texts are unchanged. Checked by tests and a six-week run on a copy of the real database (at most one a day; their birthday on its day); not measured on replies, since no note text changed.

