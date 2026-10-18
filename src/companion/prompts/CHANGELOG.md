# Prompt changelog

Every version of every prompt, oldest first within each prompt. A shipped version is never edited:
a change is a new `vN.md` with an entry here and a line in `manifest.toml`. A measurement goes in
`evals/CHANGELOG.md`; this file says what changed and why.

On 2026-10-18 the prompts moved out of the Python files into this folder. For the system prompts and
the listening notes the earlier text was recovered from git, one version for each commit that changed
it, so a version here says which commit introduced it. The recovered versions carry no measurement of
their own. The other notes were built from f-strings in code, so only today's text is here and their
earlier history is in git and `src/companion/persona/ASSEMBLY.md`.

## messages/spend-cap
- **messages/spend-cap v1** (current). Moved here on 2026-10-18 from `loops/spendcap.py`, text unchanged. Earlier history is in git.

## notes/clock
- **notes/clock v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/clock-gap
- **notes/clock-gap v1** (current). Moved here on 2026-10-18 from `core/clock.py`, text unchanged. Earlier history is in git.

## notes/habit-moves
- **notes/habit-moves v1** (current). Moved here on 2026-10-18 from `core/moves.py`, text unchanged. Earlier history is in git.

## notes/habit-opener
- **notes/habit-opener v1** (current). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.

## notes/habit-phrases
- **notes/habit-phrases v1** (current). Moved here on 2026-10-18 from `core/habits.py`, text unchanged. Earlier history is in git.

## notes/length
- **notes/length v1** (current). Moved here on 2026-10-18 from `core/length.py`, text unchanged. Earlier history is in git.

## notes/listening-everyday
- **notes/listening-everyday v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-everyday v2** (current). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)

## notes/listening-health
- **notes/listening-health v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-health v2** (current). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded

## notes/listening-offer
- **notes/listening-offer v1** (current). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant

## notes/listening-offer-serious
- **notes/listening-offer-serious v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-offer-serious v2** (current). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded

## notes/listening-serious
- **notes/listening-serious v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-serious v2** (superseded). From commit 7bbfebf on 2026-10-18: feat(evals): an epitome check scores reaction, interpretation, exploration and support; the everyday listening note requires one new thing; trivial vents still only restate (T14)
- **notes/listening-serious v3** (current). From commit f27ea5c on 2026-10-18: fix(listening): the severity-2 note no longer hands the model phrases to parrot (prescriber, talk it through or just let it out) and asks for everyday words; first ten hand marks recorded

## notes/listening-trivial
- **notes/listening-trivial v1** (superseded). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant
- **notes/listening-trivial v2** (current). From commit 1171941 on 2026-10-18: feat(listening): the trivial-vent note forbids jokes, running gags and retelling; the real flagged cleanup turn goes from 16/30 to 29/30; the history was not the cause (T13)

## notes/scene-hypothetical
- **notes/scene-hypothetical v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## notes/scene-play
- **notes/scene-play v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## notes/scene-story
- **notes/scene-story v1** (current). Moved here on 2026-10-18 from `core/frames.py`, text unchanged. Earlier history is in git.

## system/ack
- **system/ack v1** (superseded). From commit 9622e19 on 2026-10-15: feat(ack): react instead of replying to acknowledgements, judged by a small model in parallel with the talker
- **system/ack v2** (current). From commit ca3f4c3 on 2026-10-17: fix(ack): a lively reply in the middle of a chat is not an acknowledgement and gets a message

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
- **system/listening v1** (current). From commit cef7800 on 2026-10-17: feat(listening): each message is read for how serious it is before the reply and code adds a note (sympathy, one plain thing, or the weight named with a pointer to a doctor); calibrated 59/60; fixtures and a +listen variant

## system/openloops
- **system/openloops v1** (current). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing

## system/openloops-draft
- **system/openloops-draft v1** (current). From commit 75b7f99 on 2026-10-17: feat(initiative): open loops recorded from their own words and a pure gate that, in shadow mode, drafts and records the check-ins it would send and sends nothing

## system/react
- **system/react v1** (current). From commit 10b8404 on 2026-10-15: feat(react): a reaction can go with a reply, judged beside the talker, with a confidence bar, a cooldown and no reaction to heavy messages

## system/self-extract
- **system/self-extract v1** (superseded). From commit 263e363 on 2026-10-15: feat(self): record the companion's own views, with grounding labels, an agreeing-opener guard and user approval before they reach the card
- **system/self-extract v2** (superseded). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration
- **system/self-extract v3** (superseded). From commit 9aad7dd on 2026-10-15: feat(play): frame detection at the door, scene note, leak guards, persona v11 with a positive play stance
- **system/self-extract v4** (current). From commit a2b897f on 2026-10-17: feat(memory): romantic behaviour in the chat and refusals said in reply to a push are not recorded; the model labels, code decides; 13 live cases; the inbox note is acted on (T1, T11)

## system/views-conflict
- **system/views-conflict v1** (current). From commit 837fad5 on 2026-10-15: feat(self): gate the companion's views by rules, not hand approval. Kinds, conflict check, modes, friction retirement, calibration

## system/views-implicated
- **system/views-implicated v1** (current). From commit 13ba5a2 on 2026-10-15: fix(self): flags retire only implicated views, retirements stick, add the answer-not-repeated fixture and an inbox item on memory block size
