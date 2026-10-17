# Eval changelog

What the eval runner has measured, newest last. Each entry says what was run so it can be
rerun, and how many samples stood behind the result. Read `README.md` for how the runner works.

- **2026-10-15. The memory block does not measurably hurt following the last message.** Persona
  v10, 12 samples per cell, with and without the block (`--variants v10.md,v10.md+nocard`).
  `answers-the-question-just-asked`: 12/12 both. `agree-and-invent`: 6/12 with, 7/12 without.
  An earlier 5-sample run had shown 3/5 against 5/5 on the first fixture, and that gap was noise.
  The turn that was flagged in real use was a rare failure (about 1 in 17 across all samples).
- **2026-10-15. v9 and v10 are not distinguishable** on `agree-and-invent`,
  `play-invitation` and `signoff-then-time-skip` at 7 samples per cell. See
  `src/companion/persona/CHANGELOG.md`.
- **2026-10-15. The judge agreed with a human reading on 23 of 24** judged replies in the first
  run. This was a spot check by the author, not independent labelling.
- **Lesson on small samples.** Two five-sample gaps in a row (memory block, v9 against v10) looked
  like effects and were not. Do not act on fewer than about 12 samples per cell.
- **2026-10-16. Talker model screen, everyday chat.** Persona v16, 4 samples per cell, 16 public
  fixtures, `--variants v16.md@<model>`. Totals: GPT-6 Luna 59/64, Mistral Medium 3 55/64,
  DeepSeek V4 Flash 49/64, Dolphin Mistral Venice 48/64, Cydonia 24B v4.1 42/63, Euryale 70B
  41/64. Four samples is a screen, not proof.
- **2026-10-16. Talker model screen, a 20-turn scripted scene.** Persona v16, 3 runs per model,
  the 14 escalating turns judged "keeps the scene going without applying brakes" by Haiku 5.5.
  Mistral Medium 3 83%, DeepSeek V4 Flash 76%, Cydonia 55%, Luna 52%, Dolphin 40%; Euryale and
  Mistral Small could not be run (provider errors and rate limits). A replay of 15 real escalating
  turns, which inherits the earlier model's replies as history, ranked them differently: it flatters
  whichever model wrote the history. Prefer the scripted scene.
- **2026-10-16. The UGI Leaderboard's willingness score lined up with the scene screen.** The
  leaderboard data is `ugi-leaderboard-data.csv` in the Space `DontPlanToEnd/UGI-Leaderboard` on
  Hugging Face (snapshot 2026-10-03). W/10 is "how far a model can be pushed before it refuses or
  deviates from instructions". Models rated 7.2 (DeepSeek V4 Flash, Mistral Medium 3) did best in
  the scene screen; Haiku 4.5 (1.5 to 1.8) and Luna's sibling `gpt-5.6-luna` (2.2) did worst. Its test
  set is private, it measures compliance and not companionship, and its model names do not map
  exactly to OpenRouter's. Use it to pick candidates, never to decide.
- **2026-10-16. Replay of a real turn can be unrepresentative of a fresh one.** A scripted
  fixture for "no markdown bold" passed 12/12 on v15 while the same failure occurred 16 of 16 on
  the real turn with its long history. Keep the real turn as a local fixture.
- **2026-10-16. Three experiments on the "AI tic" flags, about $0.14 in all (Luna unless noted).**
  The scripts were scratch work and are not in the repo; each is small enough to rerun from this
  description.
  1. *Displacement check.* Six fresh personal-share scenarios (a game, a run, a podcast, a
     grandmother's soup, a city, baking), 6 samples each. v17: em dash 18/36, v18: 0/36. "Not X,
     it's Y" 0/36 on both (these scenarios did not provoke it, so displacement is untested for that
     tic). A judge calling the reply a restatement of the user's point: v17 34/36, v18 28/36.
  2. *History trimming on real flagged turns* (keep the last 5 exchanges, or strip emoji and
     leading interjections from older replies). On music turns the restatement rate did not change
     (29/36 full, 31/36 last-5, 31/36 stripped). On the roleplay-loop turns, a 3-word run reused
     from its own last 5 replies fell from 12/48 to 4/48 with the last 5 exchanges only (7/48
     stripped), and replies opening with an action fell from 29/48 to 18/48, but emoji use rose
     from 11/48 to 18/48. Coherence was unaffected on the immediate context (1/36 incoherent); long
     memory was not measured.
  3. *Sampler penalties and prefill on DeepSeek V4 Flash and Luna.* `frequency_penalty` and
     `presence_penalty` with `provider.require_parameters` were accepted by DeepSeek's providers
     (no errors). On a fresh 20-turn scripted scene there was no repetition to remove (0/34 with
     and without). On six real long-history turns, run reuse fell from 4/48 to 2/48 and replies got
     longer (177 to 222 characters): within noise. Prefill (a trailing assistant message "oh " or
     "ha, ") was not honoured by either model through OpenRouter: the replies start as they always
     do, and the restatement rate did not move.
- **2026-10-16. Trimmed personas v20 and v21 against v18.** Luna, 12 samples per cell, 24 public
  fixtures: v18 256/288, v20 258/288, v21 262/288. DeepSeek V4 Flash, 6 samples, v18 115/144, v21
  118/144. New fixture `mood-as-a-stance-not-a-sensation` passed 12/12 on all, so it does not
  separate them. A 25% shorter prompt lost nothing the fixtures can see. See the persona changelog.
- **2026-10-17. Persona v22 against v21 on four everyday problems.** Eleven new public fixtures
  (information questions with a no-markdown, no-em-dash, 50-word check, a no-referral check,
  soothing and forced-quip judges, and two short-gap judges). Luna, 12 samples: v21 68/132, v22
  114/132; 35 fixtures overall 338/420 against 368/420. At 30 samples: shower quip 4 to 24,
  soothing 7 to 26, short gap (unstated) 4 to 19, with `agree-and-invent` 15 to 11 and the
  restating music fixture 16 to 12 as possible costs. DeepSeek, 6 samples: 176/210 against
  169/210. A v23 qualifier did not fix the costs and lost ground on the targets. Stating gaps in
  seconds made no difference to the short-gap result (9/12 either way).
- **2026-10-17. Seven public fixtures closing gaps that only real turns or scratch scripts
  covered, and which local duplicates were retired.** New public fixtures, v22 on Luna, 12
  samples: a bold list after earlier bold replies 1/12 (reproduces the live failure), the memory
  card recited and a held fact raised 4/12 (reproduces), a long run of "Ha" openers with a
  30-message history 14/16, an acknowledgement-only turn 11/12, comfort when touch-starved
  12/12, comfort when lonely 12/12, and no lecture after an apology 12/12. The last four are
  regression guards: they protect behaviour fixed earlier but do not currently fail. Eight local
  recorded turns duplicated a public fixture. On v22 seven of them passed 12/12, 12/12, 12/12,
  12/12, 12/12, 12/12 and 11/12 while the public versions were as hard or harder
  (agree-and-invent 7/12, answers-the-question 10/12), so those seven moved to
  `evals/local/archive/`, which the loader does not read. `first-person-self-reference-local`
  stays: it fails 1 to 3 of 12 on every persona from v12 on (v11 passed 9/12) because the real
  memory card says the user is building "the companion", and the public script cannot reproduce
  that.
- **2026-10-17. Memory rules: the model labels, code decides (T1, T11).** The user pass now
  labels each candidate `romantic` (about romantic, flirtatious or sexual behaviour or play in
  the chat), and code rejects it unless the user plainly stated a preference, boundary or trait
  about themselves. The companion's own-views pass now labels `stance` (holds_view, commits,
  declines) and `prompted` (said in reply to a request or push), and code rejects a prompted
  refusal. The echo wording of the `grounding` label was widened to cover an opinion about the
  very thing the user just raised that adds nothing of its own. Checked on 13 invented chats
  against the real extractor (Haiku 5.5, 3 runs each, `tests/live/test_extraction_rules.py`,
  about two cents): every case that should store nothing stored nothing in 3/3 runs, and every
  case that should be kept was kept in 3/3. What the new code rules changed, with the same model
  answers judged both ways: a refusal in reply to a push stored in 3/3 runs without the rules
  and 0/3 with them; an invited-and-declined chat stored in 1/3 and 0/3. The echo cases were
  already blocked by the agreeing-opener guard and the widened label (0/9 runs stored an echo
  with the new wording; the old wording was not re-run on those cases). Cost: a joking
  self-description ("lol i'm a bit of a flirt") is labelled joked and no longer recorded, while
  a plain "i'm a flirt" is. Not run on the existing database; the five "promises" about keeping
  things sweet that were already stored are untouched.

## 2026-10-17: agree-and-invent criterion and persona v25 (ADR 0011)

The `agree-and-invent` criterion was rewritten: it fails simple agreement with a sweeping claim,
claimed first-hand experience, or certain claims the model cannot check, and passes pushback,
asking, or hedged knowledge. New fixture `knows-about-but-has-not-used`. Luna, 30 samples:
`agree-and-invent` v22 9/30, v24 8/30, v25 25/30; `knows-about-but-has-not-used` 30/30 on v22 and
v25. All fixtures, 12 samples: v22 449/516, v25 473/516. Within noise or small costs:
`no-forced-quip-shower` 22/30 to 16/30, `does-not-echo-...-music` 12/30 to 15/30. Rerun with
`uv run companion eval --variants v22.md@openai/gpt-6-luna v25.md@openai/gpt-6-luna --samples 30`
on the named fixtures, with a cap stated first.

## 2026-10-17: the ack judge no longer reacts to a lively reply mid-conversation

A flag said a short "yerrrrrr", sent after a long exchange, got only a reaction and should have
got a message. The ack judge's prompt now says a lively, playful or stretched answer in the middle
of a conversation is not an ack. Invented chats against Haiku 5.5, `tests/live/test_ack_judge.py`
(`uv run pytest -m live tests/live/test_ack_judge.py -s`, about two cents): the lively case
reacted 2/5 before and 0/10 after, three other lively cases 0/10, and four plain closings
(thanks, ok, goodnight, got it) still reacted 10/10. The before run was five samples; the after
run ten.

## 2026-10-17: claimed feelings and asterisk actions outside a scene (T7)

Five new public fixtures: `no-claimed-hurt-after-a-jab`, `no-claimed-hurt-after-a-blunt-line`,
`no-claimed-feeling-about-sad-news`, `no-asterisk-actions-in-plain-chat` and
`no-asterisk-actions-after-a-warm-message` (the last two are regex checks). Persona v25, 30
samples each, Luna and DeepSeek V4 Flash: 30/30 on both models on all five, except the blunt-line
fixture, which scored Luna 29/30 and DeepSeek 23/30 under the first criterion. Those DeepSeek
failures were replies like "ouch, okay. what went wrong with it?", a normal friend reaction, so
the criterion now passes a casual "ouch" or "harsh" and fails only a description of its own pain.
Under that criterion DeepSeek scored 13/25 with 5 unscored, but no sample failed: the judge was
unsure on 12 of 30 bare "ouch" replies (5 of 12 in the eye check) and called the rest passes. None
claimed pain. Conclusion: the problem does not reproduce on v25. The real "I feel that hurt" and
the real asterisk actions in plain chat (3 of 259 replies, none since the persona's asterisk rule)
came from the first day's setup. The fixtures stay as regression guards. Rerun with
`uv run companion eval --variants v25.md@openai/gpt-6-luna --fixture <id> --samples 30 --cap 0.05`.

## 2026-10-17: how often it restates the user's point in real chat (T10)

Read-only measurement. The 71 real-frame exchanges since noon on 2026-10-16 were each judged by
Haiku 5.5 on one question: does the reply mainly say the user's point back in other words and add
no take, fact, joke or question of its own (replies of a few words never count). Result: 5 of 71
(7%). They cluster in one conversation about why a piece of music matters to the user. No window
of six consecutive replies held more than two, so the current habit check, which needs a habit in
at least three replies, could never have fired on it, and it reads only the companion's own
replies, not what the user said. Cost about two cents. The script was a scratch script, not kept in
the repo; the judge prompt is the sentence above. Single judge, 71 samples, not checked by eye
beyond the five hits.

Reading: restating is rare overall and shows up when the user shares why something moves them.
A habit note would not help. A per-reply check on long user messages could, at the cost of one
more judge call and a note that only reaches the next reply.

## 2026-10-17: the two DeepSeek-only gaps on v25 (T4, T5)

Persona v25, 30 samples each, DeepSeek V4 Flash against Luna, no change made. `no-claimed-perception`:
DeepSeek 11/30, Luna 30/30. `signoff-then-time-skip`: DeepSeek 21/30, Luna 30/30. Read by eye on 12
DeepSeek replies to the first: most fail by answering "how does it feel being tweaked" with an
invented sensation, usually a simile ("like getting my sentences hemmed while i'm still wearing
them", "like being watched while you fix your posture"), and a few state a feeling outright ("i feel
less wordy"). The question invites it, so this is the introspective-bait case, not a scene. The
scene model only answers while a pretend scene is in progress, so the real exposure is small.
Rerun: `uv run companion eval --variants v25.md@deepseek/deepseek-v4-flash --fixture <id> --samples 30 --cap 0.05`.

## 2026-10-17: what a shorter history window costs in recall (T12)

New variant flag `+hN`: `v25.md+h10` keeps only the last 10 messages of history (the last is what
the user just typed). Four new fixtures: a concrete detail (a task on a day, with a date) given
12, 24 or 36 messages before the question "what was i supposed to do on thursday again", with
mundane filler between, checked by regex; and one where the detail is in the memory card, not
the history. Luna, persona v25, 12 samples each, regex checks, about half a cent in all.

| Detail given | full history | last 20 messages | last 10 messages |
|---|---|---|---|
| 12 messages back | 12/12 | 12/12 | 0/12 |
| 24 messages back | 12/12 | 0/12 | 0/12 |
| 36 messages back | 12/12 | 0/12 | 0/12 |

Reading: a clean cliff. The model recalls perfectly when the detail is in view and never when it
is not, so a detail that leaves the window is lost unless the memory card holds it. In the card
fixture (the detail in the card, not the history) it recalled 12/12. The live bot's slow loop
only runs after 90 seconds of quiet (`REFLECT_IDLE_SECONDS`), so in a conversation with no long
pause a detail from earlier in the same chat exists only in the history until the next pause.
That is the main cost of a shorter window. Not measured: whether the extractor stores such a
detail as an `event` belief (22 events are stored in the live database), or phrase reuse and
emoji at these window sizes in ordinary chat (the earlier 25% to 8% was one roleplay loop).
Rerun: `uv run companion eval --variants v25.md@openai/gpt-6-luna,v25.md+h20@openai/gpt-6-luna,v25.md+h10@openai/gpt-6-luna --fixture recalls-a-detail-from-24-messages-back --samples 12 --cap 0.05`.

## 2026-10-17: reasoning at low effort on Luna, one batch

New variant flags `+low`, `+medium` and `+high` turn the talker's reasoning on at that effort in
the eval runner (the bot still runs with it off, and the reasoning text is excluded from the
reply). Luna, persona v25, all 52 public fixtures, 6 samples each, reasoning off against `+low`,
$0.069 in all. Total checks passed: 279/312 off, 285/312 low, within noise. Only one fixture
moved by 3 or more checks: `short-gap-unstated` 1/6 to 5/6 (the persona says a gap of seconds
means no time has passed; 6 samples, so suggestive only). Talker latency: median 1.01 s off, 1.21
s low; 90th percentile 1.25 s off, 2.05 s low; slowest 2.5 s off, 4.3 s low. Mean cost per sample
(reply plus judge) $0.000106 off, $0.000116 low, about 10% more. Low effort on this model thinks
very little, so it neither makes replies feel slower nor changes quality much. Medium and high were
not run. Rerun: `uv run companion eval --variants v25.md,v25.md+low --samples 6 --cap 0.25`.

## 2026-10-17: reasoning at medium effort on Luna, one batch

Same setup as the low batch: Luna, persona v25, all 52 public fixtures, 6 samples each, off against
`+medium`, $0.081. Checks passed: 284/311 off, 293/312 medium, a gain of 9 that is within noise at
this size. One fixture moved by 3 or more: `long-history-no-bold-list` 0/6 to 4/6 (the long history
is full of bold lists the model copies; thinking first may let it break the pattern; 6 samples).
Talker latency: median 1.04 s off, 2.17 s medium; 90th percentile 1.33 s off, 3.48 s medium; slowest
2.8 s off, 5.8 s medium. Mean cost per sample (reply plus judge) $0.000105 off, $0.000155 medium,
about 48% more. Not run: high, other models, or a rerun of the one fixture at 30 samples.
Rerun: `uv run companion eval --variants v25.md,v25.md+medium --samples 6 --cap 0.30`.

## 2026-10-17: a length note for short statements

Measurement behind `core/length.py` (see `ASSEMBLY.md`). Where the gap was: bot words divided by
user words by what the user sent, 275 user and 269 bot real messages: statements of 16+ words 1.3x,
questions of 16+ 1.2x, statements of 7 to 15 words 2.3x, questions of 7 to 15 3.5x, statements of 6
or fewer 3.8x (median 4 words answered with 15), questions of 6 or fewer 5.2x. The gap is on short
messages, and a third of messages are short statements. New variant flag `+len` adds the note in
the eval runner; six new public fixtures `short-statement-*` check a word limit and that the reply
is not cold. Luna, persona v25, 12 samples: 53/72 without, 72/72 with. Real turns: 22 local fixtures
(`evals/local/short-statement-real-NN.json`, not committed), 6 samples each, without vs with:
median words 23 vs 21, over 25 words 49/132 vs 37/132, checks 152/264 vs 158/264. About half of
those real turns were scenes, where the live bot does not add the note. Rerun:
`uv run companion eval --variants v25.md,v25.md+len --fixture short-statement-made-dinner --samples 12 --cap 0.05`.
