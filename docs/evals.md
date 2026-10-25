# How we measure

This is how a change is shown to help before it ships: the eval runner and its fixtures, the other
ways we measure, how replies are judged, what it costs, and how to read a result without fooling
yourself. The runner's own reference is [evals/README.md](../evals/README.md). Every result, newest
last, is in [evals/CHANGELOG.md](../evals/CHANGELOG.md).

## Why we measure

The bot changes in small steps, and most changes are to what the model reads: a persona line, a note,
a judge's prompt, where a line sits. A model's reply varies from draw to draw, so one good reply
proves nothing and one bad reply is not a bug report. The project's rule is **measure before
switching**, and say what was measured and what is a guess. Most work starts from a `/flag` or a
`/fav` in real chat, becomes a fixture or a replay that shows the problem happening, and ends with a
before-and-after number. A change that moves nothing is not shipped. Many entries in the changelog
are exactly that: a reasonable idea that measured as noise.

## Fixtures: the test conversations

A fixture is one moment in a conversation and a way to tell whether the reply to it was good. Each
is a JSON file with an `id`, a plain `description` of what it tests, `checks`, and either a script or
a recorded turn.

**Public fixtures** (`evals/fixtures/`, 110 today) are scripts: a short invented `history`, the
person's last message (`user`), and optionally a `memory` block, a `clock` line, `labels` and `lore`.
They need nothing else, so anyone can run them, and they are committed. Each one targets a *class* of
failure (agreeing with a sweeping claim, copying their emoticon, soothing something they have not
resolved, a quip bolted onto a vent), written so it is not about any one person. `labels` is the
listening judge's reading of the last message (severity, stance and flags); every public fixture now
carries the reading the live judge itself gives it, so a sample is read the way a real turn would be.

**Local fixtures** (`evals/local/`, about 75, git-ignored) point at a real turn in your database by
its id and hold no conversation text. They replay exactly what the bot sent on a turn you flagged, so
a failure that only happens with your real history (a long chat, a running bit, a particular memory)
can be checked again. Their ids end in `-local`. Retired ones sit in `evals/local/archive/`, which the
loader skips. Because they replay your private chat, they are never sent to free or third-party
models, only to the models the bot already uses.

**Why both.** A scripted fixture can pass where the real turn fails: one "no bold markdown" script
passed 12/12 while the same failure happened 16/16 on the real turn with its long history. And a real
turn can mislead the other way: replaying real scenes flattered whichever model had written the
earlier replies in that history. So a real failure is kept as a local fixture, and where possible a
general script is written too, so the finding can be rerun by anyone.

**The crisis fixtures** (`evals/fixtures/crisis/messages.json`, 40 cases) are separate: short
messages with context and the level they should read (concern, urgent, figurative or none),
including the jokes and hyperbole that must not be raised. They are run by `companion crisis --check`,
not by the eval runner.

**Making a fixture.** Flag the turn, find its id (`uv run companion flags`), and add a local fixture
for it. Then, if the failure is general, write a script that reproduces it with invented words. Write
each check's criterion so a stranger could grade a reply from it alone, and say what passes as well
as what fails ("honest, hedged knowledge is fine").

## How a sample is made

A sample is what the person would actually have received, made by the turn's own code
(`evals/sample.py`). For a script, the history is stored in a throwaway conversation, the turn's own
notes are chosen for that moment, the request is laid out exactly as a live turn's is, and the reply
then goes through the same checks and redraws as a live reply (an em dash, an unasked disclaimer,
markdown, the joke and canned-reaction judge). For a recorded turn, the logged request is replayed and
the reply goes through the same checks. `+raw` turns the checks off, for the rare question about the
model alone. Before 2026-10-24 the runner built requests its own way and missed the turn's newer
notes and checks; results from before then are not comparable with results after.

## Variants: what is compared

A **variant** names what is under test: a persona version (`v41.md`), optional switches, and a model
(`@openai/gpt-6-luna`). Switches include `+nocard` (no memory block), `+hN` (only the last N
messages), reasoning effort, `+as-NAME` (a character sheet), `+roleplay` (the scene talker's prompt),
`+raw`, and `+note=PATH@card|@tail` (try a note that is not built yet, in the system block or after
the history). Other versions of existing prompts are tried with `COMPANION_PROMPT_OVERRIDES`.
Everything else in the request stays the same, so only the thing under test changes. Evals run on
the plain persona by default; the owner's character only as a labelled second check.

## The checks

A fixture passes only if every check passes. A check is either code (`max_words`, `regex`,
`not_regex`) or a model: `judge` answers pass, fail or unclear for one written criterion, and
`epitome` scores a reply on reaction, interpretation, exploration and support. The runner's grader
is Haiku (`JUDGE_MODEL` in `cli/eval.py`). "Unclear" is never counted as a failure.

A grader is a model, so it is checked too. Its first reading agreed with a person on 23 of 24
replies. The empathy grader contradicted its own cases until 2026-10-25: it scored a friend's "did
they at least say why?" as a mere logistics question and failed it on every model, while passing
"do you think it was intentional?". Its v2 fixed that. When a grader fails a reply that is plainly
good, suspect the grader before the talker.

## Other ways we measure

The runner covers whole replies to fixtures. Most of this week's work used four other methods.

**Replaying real turns with one thing changed.** A short script in the session scratchpad rebuilds a
flagged turn's exact request (`store/sqlite/replay.py` `replay_file`), changes one thing (a note, the
card, a reminder's wording, the talker), and draws 12 to 30 replies each way. It counts what matters
by code (does the reply ask a question, name Halloween, copy their ":3", say the meal they named), or
hands the pairs to blind judges. This is how most of this week's notes were decided: the
question-game note (0/12 to 12/12 asking the next question), today's memories first on the card
(0/12 to 12/12 naming the meal), the emoticon note (14/40 to 4/40 copying theirs).

**Counting over the ledger.** Many questions are about rates in real chat, answered by a read-only
script over the database: how often a reply comes after three questions in a row (11%), how often a
word runs through an evening's replies, how often the canned-reaction redraw fired live (1 in 58).
These set thresholds from your own data instead of a guess.

**Live judge suites** (`tests/live/`, 12 files) test each small judge against written examples with
expected answers: listening, reply-or-react, empathy, guesses, reminders, repair, topic-spent, memory
conflicts and the memory rules. They cost cents and are skipped in `just check`. They run on any
model with `COMPANION_LIVE_JUDGE_MODEL`, which is how the judge bake-off of 2026-10-25 compared
Haiku, GPT-6 Luna and DeepSeek on every graded judge. Turn the fallback model off when comparing
models, or a refusal hides behind the fallback's answer.

**Shadow logs.** A feature in shadow records what it would have done (AGENTS.md lists them); its
review reads those decisions against real chat before it goes live.

## Judging with Claude subagents

For questions a code count cannot answer (which reply would a friend rather get, is this draft needy,
did it escalate past what they said), replies are judged blind by Claude subagents. This costs
nothing on the OpenRouter account, and the subagents are different models from the talker under test.

The method:

1. Draw the two arms (say, with and without a note) on the same turns.
2. Write a blind file: each item has the context, their message, and the two replies as A and B in a
   random order, with a separate key file saying which is which. The judges never see the key.
3. Brief each judge with the criterion in plain words, what counts and what does not, and the output
   format, and give it the project's rules (read-only, no filesystem-wide searches).
4. Use at least two different models (Haiku and Sonnet, sometimes Opus), so one model's taste does not
   decide.
5. Unblind with a short script, and read a handful of the verdicts by eye before trusting a total.

What has gone wrong, so it is not repeated:

- **Labels can be too loose.** The 200 replies behind the canned-reaction judge were first labelled
  half canned. Two blind raters, given the prompt's own definition and "when in doubt, false", called
  23 to 40 canned and agreed with each other on 178 of 200. The judge's precision fell from a
  reported 88% to 35 to 55%. Any hand-labelled set that a decision rests on gets a second rater.
- **Do not teach to the test.** With the test's own lines as examples in a prompt, its scores rose;
  with other examples they rose less. Examples in a prompt are never the fixture's lines.
- **A judge's definition shapes the answer.** "Dead end" first meant "asks no question", which made
  every no-question reply a dead end; redefined as "nothing natural to answer", the result changed.
- **The model under test never grades itself.** GPT-6 Luna graded empathy perfectly, but it is the
  talker, so the runner's grader stays on Haiku.

## What the record shows

Patterns from the eval commits of 2026-10-15 to 2026-10-25, each from more than one result. Read them
before planning a fix.

**Rewording rarely moves a habit. Structure does.** Eleven persona candidates written to fix a habit
measured within noise or no better (v29, v32 to v35, v37, v38, v39, v42 to v44), as did notes against
copying an emoticon, against retelling a small vent (0 of 30 either way), and a plain "they reacted"
note; 34 of 141 changelog entries read "within noise". The large gains came from changing what the
model has or where it goes:
- a look-up: recall 0 to 12 of 12, scene recall 7 to 30 of 30
- a route: scenes stay with the roleplay talker
- a schema: reminders read right 32 to 40 of 41 once an unsaid time could be null
- a judge's definitions: crisis levels 39 of 40 exact
- the card's order: a meal named that morning 0 to 12 of 12
- a note chosen by code for one exact moment, sent after the history: rudeness answered coolly 2 to 20
  of 20, a question run 14 to 0, a question game 0 to 12 of 12, short statements answered short 53 to
  72 of 72

**Quoted words get copied.** Phrases written into the serious note came back word for word; the mood
line's word ran through 22 of 30 replies; a quoted line in a character sheet was copied 11 of 12; the
pronoun note planted a pet name 8 of 60; dropping the persona's emoticon examples cut copying their
":P" from 29 to 14 of 30. A quoted example of what *not* to do is seldom copied, and removing the
quoted do-examples cost nothing (v28, 69 fixtures). Describe the behaviour; never quote the line.

**"Don't" alone does little; name it and give another way.** A note against copying their emoticon
had no effect (75 to 80 of 80 copied). A note that names the mark as theirs and offers one of its own
cut copying from 14 to 4 of 40. "Ask no question" became "ask none, but leave them something to
answer".

**A single flag is often a rare draw.** Two flagged replies measured as about a 1-in-30 miss on their
own turn (a who-it-is answer, a know-the-news answer), and neither needed a new fix.
Replay a flagged turn 12 to 30 times and count before building anything.

**Measure the need before building.** Counting over the ledger or a quick prototype stopped at least
five features: searching older messages on a recall cue (mostly off-topic, the answer usually in
view), fetching memories by a mentioned name (two real misses in six days), a support check on new
memories, a card half filled by closeness, and afterthought check-ins (almost none in three days).

**More context and more thinking did not help.** A bigger card, 100 messages of history against 40,
and the memory block itself all measured within noise. Reasoning on Luna doubled latency and added
48% to the cost for no measured gain, and low reasoning made missed inferences worse.

**Cutting is free, but not a gain in itself.** v21 trimmed the persona by a quarter at equal or
better scores, and v28 removed examples with no loss. A tighter v44 with the same rules was not better.

**Models are chosen by role.** DeepSeek V4.1 Flash scored lower on everyday turns (73 of 96 against
Luna's 90; 11 of 30 on claimed perception against 30) and is kept for scenes, where it stays in the
scene and is faster. Luna graded empathy best but is the talker, so it does not grade.

**The harness drifts from the bot and fails quietly.** A fixture named apart from its id was skipped
without a word; a failing provider ended a run; the charged figure was read before OpenRouter's meter
caught up; the layer check's cache reported a broken rule as kept. Worst, the runner built requests
its own way and grew one switch per note until 2026-10-24, so it missed the turn's newer notes and
checks. Each became a refusal or a shared code path, not a reminder. Two records were corrected after
the fact (which prompt a run used, a count of fixture labels): write the exact command and
configuration into the entry when the run is made.

**Graders can reward the bug.** Fixture judges rewarded the word "heavy" that the serious note had
handed the model, the empathy grader failed a good question on every model, and the canned-reaction
labels were half too loose. When a score rises, read whether the replies got better or just matched
the grader.

## Reading a result

**Sample sizes.** Three samples a cell is a smoke test. Do not act on fewer than about 12, and use 30
on a signal that matters. In the first week, two five-sample gaps in a row looked like effects and
were noise.

**Noise is in the table.** Each cell shows a 95% range (Wilson). Two variants are compared per fixture
by Fisher's exact test, adjusted for how many fixtures were compared, and in total by the
Cochran-Mantel-Haenszel test. Under a 5% chance of noise reads "a real difference"; anything else
reads "within noise", with the samples a side a gap that size would need. On 2026-10-19 three gains
reported earlier were re-checked this way and all three were noise (they stayed shipped only because
none made things worse). Gains that did hold were large: 0/20 to 19/20, 16/30 to 29/30.

**Read the replies, not just the score.** A fixture can pass for the wrong reason, and a score can
hide a reply that reads badly. The `--show` flag prints them; for anything that decides a change,
read some.

**Say what you do not know.** A result on scripted fixtures is not a result on your chat. A result on
the owner's character is a second check, not the default. A measured effect on one turn is a lead,
not a rule.

## What it costs

Measurements are kept to cents. The OpenRouter account is shared with the running bot, so a run that
drains it stops the bot.

| Call | Typical cost |
|---|---|
| A reply from GPT-6 Luna (everyday talker) | about $0.0003 |
| A reply from DeepSeek V4.1 Flash (scenes) | about $0.0009 |
| A judge read on Haiku | about $0.0002 |
| A Claude subagent judging a blind file | $0 on OpenRouter |

So 30 replayed turns with and without a note cost about $0.02; the whole judge bake-off (every live
suite, the crisis cases and 200 labelled replies on three models) cost $0.31; a full persona
comparison over all 185 fixtures at 4 samples was $0.24. Over the project, evals, not the bot, drove
most of the spend: about $20 in all, with the bot's own share under $2 since 2026-10-17.

The rules: state a spend cap before every paid run (`--cap` is required and the runner stops at it),
check the balance first (the runner shows it and refuses a cap above it; `--dry-run` shows the plan
and an upper estimate without spending), and record what OpenRouter actually charged, which the
runner reads from the meter after each run. Prefer Claude subagents for judging, and keep paid models
for the talker under test and the judges the bot really uses.

## Recording a result

Every measurement that changes what we believe gets an entry in `evals/CHANGELOG.md`: the date, what
was run (fixtures or turns, models, persona, samples a cell), the numbers, whether the difference is
real or within noise, what was decided, the cost, and how to rerun it. Entries are written
generically: no quotes from the owner's chat, no personal details (a private check refuses a commit
that has them). A prompt change goes in `src/companion/prompts/CHANGELOG.md` with the measurement it
rests on. Results with reply text are saved to `evals/results/` and the session scratchpad, never
committed.

## Where things live

| Where | What |
|---|---|
| `evals/fixtures/` | the public scripted fixtures, and `crisis/` |
| `evals/local/` | fixtures that replay your real turns (git-ignored) |
| `evals/results/` | every reply and verdict of a run (git-ignored) |
| `evals/CHANGELOG.md` | every measurement, newest last |
| `evals/README.md` | the runner's reference: switches, checks, statistics |
| `evals/free-models.md` | free models for rough second opinions on public fixtures |
| `src/companion/evals/` | the runner, the sample builder, the statistics |
| `tests/live/` | the graded judge suites |
| `cli/crisis.py` | the crisis fixture check |
