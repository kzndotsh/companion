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
- **system/persona v36** (shipped 2026-10-19). v31 with the mood line changed for ADR 0016: "a mood that can carry across a conversation" and "Say a mood as a stance, in words ('kind of scattered tonight', 'in a good mood')" become "If they ask how you are, answer in plain words, never as a sensation in a body; otherwise let how you feel show in how you write rather than announcing it." Reason: code owns the mood now and shows it only in behaviour; v31 volunteered "in a pretty mellow mood" when asked what it was up to (6 to 8 of 30), and quoted examples get parroted (T15). Measurement in `evals/CHANGELOG.md`.
- **system/persona v37** (dropped: more jokes, not fewer). v36 with the banned-joke list for ordinary mentions ("Do not build a joke out of it: no personifying ... no 'side quest', 'era', 'roulette' or 'plotting against you' framings. A plain reaction beats a clever one.") replaced by a positive ending rule: "react plainly or ask a plain question, then stop. Say the one thing you mean and end there, on the reaction or the question, without a second line to round it off." Reason: J45, a joke tacked onto a fine reaction in about half the samples on five flagged turns; a 2026 preprint suggests naming forbidden framings primes them. Measurement in `evals/CHANGELOG.md`.
- **system/persona v38** (dropped: within noise of v36). v36 keeping the banned-joke list, with the ending rule added after "A plain reaction beats a clever one.": "Say the one thing you mean and stop there, without a second line to round it off." Reason: v37 (the rule without the list) made the jokes worse, so this tests whether the rule helps on top of the list. Measurement in `evals/CHANGELOG.md`.

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

## messages/spend-cap
- **messages/spend-cap v1** (current). Moved here on 2026-10-18 from `loops/spendcap.py`, text unchanged. Earlier history is in git.

## notes/address
- **notes/address v1** (current). New. "How they want to be referred to: $address. Use it every time, without bringing it up." Filled by `core/address.py` from a setting they state (`companion address --set`), and placed right after the clock line on every turn. Reason: on 2026-10-19 the memory card (15 of 196 memories) crowded out how they want to be referred to, and a reply got it wrong.

## notes/clock
- **notes/clock v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/clock-gap
- **notes/clock-gap v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/habit-echo
- **notes/habit-echo v1** (dropped, never live; `+echo` in evals adds it when their message has an emoji or emoticon, `core/habits.py`). Owner's flag of 2026-10-18: it only used :P and :3 when they did. Across the history the reply had one 14 times in 39 after a message with one, always the same one, and 12 times in 533 otherwise. The note names no emoji so it cannot hand one over. Dropped: no effect, 7 of 80 replies avoided copying without it and 8 of 80 with it. Measurement in `evals/CHANGELOG.md`.

## notes/habit-moves
- **notes/habit-moves v1** (current). Moved here on 2026-10-18 from `core/moves.py`, text unchanged. Earlier history is in git.

## notes/habit-opener
- **notes/habit-opener v1** (current). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.

## notes/habit-phrases
- **notes/habit-phrases v1** (current). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.

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
- **notes/listening-serious v5** (current). v4 without "Keep the whole reply under about 35 words": the number moved to `core/length.py`, the one place a length target is chosen, and reaches the model as `notes/length-serious`. The words the model reads for a serious message are the same; they now come from two notes.

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
- **notes/listening-trivial v2** (current). From commit 1171941 on 2026-10-18: feat(listening): the trivial-vent note forbids jokes, running gags and retelling; the real flagged cleanup turn goes from 16/30 to 29/30; the history was not the cause (T13)
- **notes/listening-trivial v3** (not shipped: no change on the flagged turn). "React in a few words of your own ... and stop there. Do not describe their situation back to them, not even as a \"when you...\" clause saying why it is annoying: they know why." Reason: a real minor vent was answered 30 of 30 times with "that's so annoying when you're ready to crash and the bed's still waiting on laundry" (owner flag "repeating", T14). Measurement in `evals/CHANGELOG.md`.
- **notes/listening-trivial v4** (not shipped: no change on the flagged turn). v3 with "Keep the whole reply under about six words." to test whether a length limit removes the retelling clause. Measurement in `evals/CHANGELOG.md`.

## notes/mood-buzzing
- **notes/mood-buzzing v1** (dropped). The buzzing line from ADR 0016 (quick and lively, stretched words, an exclamation mark or emoji), shown by the `+mood-buzzing` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-buzzing v2** (dropped). "Lots of energy", and asks for it in words, not only emoji (v1 mostly added ✨), and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`. Dropped with v1: neither made replies livelier in words (v1 added emoji, v2 changed nothing outside noise), and the persona already matches an excited message in the moment (J4), so buzzing is not a state of its own for now.

## notes/mood-cozy
- **notes/mood-cozy v1** (superseded). The cozy line from ADR 0016 (relaxed, warm, unhurried, a bit affectionate, a bit shorter), shown by the `+mood-cozy` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-cozy v2** (candidate, eval only; current). Describes the behaviour without the word "cozy", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/mood-flat
- **notes/mood-flat v1** (superseded). The flat line from ADR 0016 (shorter and plainer, no emoji, never asks to be cheered up), shown by the `+mood-flat` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-flat v2** (candidate, eval only; current). "Lower energy than usual" instead of "flat", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/mood-playful
- **notes/mood-playful v1** (superseded). The playful line from ADR 0016 (more teasing and silly asides), shown by the `+mood-playful` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-playful v2** (candidate, eval only; current). "You feel like teasing and joking" instead of "a playful mood", and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/mood-tender
- **notes/mood-tender v1** (superseded). The tender line from ADR 0016 (softer and more attentive after something hard; never brings it up or asks if they are okay), shown by the `+mood-tender` eval flag to measure whether a mood line changes replies before any mood is built (TODO J5, M1). The bot never sends it.
- **notes/mood-tender v2** (candidate, eval only; current). Says "be softer" instead of naming a state, and "never describe your own state" instead of "never mention your mood". Reason: with v1 the mood word bled into replies (22 of 30 rain replies with the cozy line said "somewhere cozy"). Measurement in `evals/CHANGELOG.md`.

## notes/recall
- **notes/recall v1** (current). The beliefs the recall look-up found, shown for that turn only, under "They asked you to remember this". Filled by `core/recall.py`.

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

## system/frames
- **system/frames v1** (current). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance

## system/habits
- **system/habits v1** (superseded). From commit 005c5b4 on 2026-10-15: feat(moves): a model reads the last replies in the background and names what repeats; the next turns get a note
- **system/habits v2** (current). From commit ec5fdc5 on 2026-10-15: feat(persona): v16 plain-text rule; habit check drops habits seen in fewer than three replies; fixtures

## system/judge
- **system/judge v1** (current). From commit 973b63b on 2026-10-15: feat(evals): replay recorded turns against persona variants, with a judge, a spend cap and nine fixtures

## system/judge-empathy
- **system/judge-empathy v1** (current). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)

## system/listening
- **system/listening v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **system/listening v2** (superseded). v1 plus one label, rude: plainly rude or hostile toward the companion itself, false for teasing, banter, a light jab, blunt feedback or frustration at something else. It feeds `notes/rude`. Reason: the reflex to apologise and offer more after an insult held against a character sheet in 8 of 20 replies (J1, 2026-10-18).
- **system/listening v3** (current). v2 plus recall (they asked the companion to remember or already know something about them) and topic (what to look up, worked out from context when the message is vague). Reason: "come on, you know this one..." about their favourite food got a guess and a joke, with three burger beliefs in memory and none on the card (owner's flag, 2026-10-18).

## system/openloops
- **system/openloops v1** (superseded). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing
- **system/openloops v2** (superseded). Each loop also carries a certainty (firm, maybe, wish) and whether it is about the companion, and code keeps only firm plans not about the companion: in shadow mode all four open loops were "maybe someday" statements or about the bot (adding vision), recorded although v1 said not to list things about the companion. The same call now also reports which open loops their new messages already settle, so code closes them as resolved and the companion never asks how something went after they told it. From the proactive-messaging review of 2026-10-18 (modality separates a plan from a wish).
- **system/openloops v3** (current). v2 plus a kind for each loop: follow_up (asked about the morning after, as before), celebrate (their birthday or anniversary, marked on the morning of the day) or encourage (something big they face on a known day, a word of encouragement early that morning). Code picks the time from the kind; a celebration or encouragement without a day after today is not recorded, and either one expires at the end of its day. Reason: a birthday was scheduled for the morning after, so the companion would have asked how the birthday went instead of saying happy birthday.

## system/openloops-draft
- **system/openloops-draft v1** (superseded). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing
- **system/openloops-draft v2** (current). The draft is told the loop's kind: follow_up asks how it went, celebrate wishes them well for the day, encourage cheers them on before it. Same limits as v1.

## system/quip
- **system/quip v1** (superseded, never live). New. Reads one exchange and says whether the reply added a constructed joke on top of reacting (a quip, pun, punchline, wry aside, personification); playing along with their own joke does not count. Used by `core/quip.py` to choose one fresh reply instead (J45). Measurement in `evals/CHANGELOG.md`.
- **system/quip v2** (current). Looks at the user's message first: anything playful, flirty, teasing or joking is false, so banter they started is never resampled; only a joke bolted onto an ordinary message counts, and doubt is false. Reason: v1 fired on 27 of 100 real ordinary turns and about half were fine (playing along with flirting, plain questions). Measurement in `evals/CHANGELOG.md`.

## system/react
- **system/react v1** (current). From commit 10b8404 on 2026-10-15: feat(react): a reaction can go with a reply, judged beside the talker, with a confidence bar, a cooldown and no reaction to heavy messages

## system/recall
- **system/recall v1** (current). New. The look-up when they ask it to remember: a topic and every candidate belief, labelled; it returns at most five labels that bear on the topic. Code keeps only labels it showed and never a crisis-level belief (`core/recall.py`).

## system/self-extract
- **system/self-extract v1** (superseded). From commit 263e363 on 2026-10-15: feat(self): record the companion's own views, with grounding labels, an agreeing-opener guard and user approval before they reach the card
- **system/self-extract v2** (superseded). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration
- **system/self-extract v3** (superseded). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance
- **system/self-extract v4** (current). From commit a2b897f on 2026-10-17: feat(memory): romantic behaviour in the chat and refusals said in reply to a push are not recorded; the model labels, code decides; 13 live cases; the inbox note is acted on (T1, T11)

## system/views-conflict
- **system/views-conflict v1** (current). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration

## system/views-implicated
- **system/views-implicated v1** (current). From commit 13ba5a2 on 2026-10-15: fix(self): flags retire only implicated views, retirements stick, add the answer-not-repeated fixture and an inbox item on memory block size
