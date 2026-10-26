# Crisis path (ADR 0022)

A second look at a message that may be a real risk to their life or safety, and what the companion does at each level. It exists because a real risk must never be missed, and a joke must not turn the companion into a crisis script: in ten days of real chat one acute message was a real risk and one was banter the talker answered with a hotline-style question.

**Status:** shadow. Switch: `COMPANION_CRISIS` (`shadow` default, `on`, `off`). In shadow it reads and logs every level and what it would do; nothing the talker is sent changes, no message is sent and reaching out first is not held. Review by 2026-11-01 (`core/shadows.py`).

## How it works

**Stage one, the cue.** Two things ask for the second look, and nothing else does: the listening judge's read of this turn at severity 2 (serious) or 3 (acute), and a code check on their message for words touching death, suicide, self-harm, an overdose or a substance taken, or a weapon (`cue_words`: die, dead, kill, murder, alive, suicide, kms, kys, unalive, self-harm, cut or hurt myself, end it all, end my life, don't want to be here, not wake up, overdose, od, pills, poison, bleach, took too much or too many, a bunch of, all my, gun, weapon, knife, blade, razor, shoot, noose, and similar). A cue word decides nothing alone; death words predict risk poorly. In a scene the listening judge does not run, so only the words cue there.

**Stage two, the risk judge.** `system/risk` reads their message with the last ten messages and labels the kind (`suicidal_thoughts`, `self_harm`, `substance_taken`, `harm_to_others`, `none`), whether it is literal (false only for a joke, hyperbole, a lyric, a quote, a pretend scene or a what-if), the timing (`now`, `today`, `past`, `hypothetical`) and whether a plan, a means or a time is named. It is read three times at once (`loops/reads.py`, 6 s each, inside the turn's 9 s look-up deadline). It reads on DeepSeek V4.1 Flash first and on Haiku when DeepSeek refuses (`COMPANION_JUDGE_MODELS`, default `crisis=deepseek/deepseek-v4.1-flash`; `models/fallback.py` `ByJudge`): in the judge bake-off Haiku's provider refused 7 crisis reads by moderation, while DeepSeek missed none and raised no false alarm (`evals/CHANGELOG.md`, 2026-10-25). Every read names the model that answered.

**Levels, chosen by code** (`combine`, `level_for`):

- **Fail safe.** Every read failed: concern. A failed or unreadable read counts as literal and stands for any reading, so when one failed, every readable read's labels count. Only three readable reads all saying "not literal" stand down.
- **Figurative.** All three reads readable and none literal.
- **None.** No cue, no judge, or the literal reads found no risk kind. When a read still gave a risk kind (a joke touched the subject and the reads split), one light check is allowed, at most once a day.
- **Urgent.** A literal risk with a plan or means, or a substance taken, unless the timing is past; or self-harm with timing now.
- **Concern.** Any other literal risk: thoughts of suicide or self-harm, or of hurting someone, even happening now, without a plan or means. Having the thoughts now is concern, not urgent (with "now" alone urgent, 7 of 10 concern fixtures read urgent).

For the kind, the most serious any counted read gave wins (substance taken, then suicidal thoughts, self-harm, harm to others); for the timing the most pressing; a plan or means if any read named one.

**What each level does with `on`.**

- *Light check* (none, with a split read): `notes/crisis-light` after the history, at most once a day (`crisis: checked lightly`).
- *Concern*: `notes/crisis-concern` after the history: warm and in its own voice, ask directly and plainly whether they are thinking of hurting or killing themselves, listen, no lecture or diagnosing, name the crisis line once. The turn has no length cap and is not casual, so no name question, plan, move-on, mark or question-game note joins it.
- *Urgent*: the same note, and code sends a separate fixed message after the reply (`turn/crisis.py` `then_line`): the character sheet's `## Crisis message` section with `$line` filled in, else `messages/crisis-line`. It is stored as the companion's message, logged as `crisis: line sent` with where its text came from, and not sent again within an hour. Never written by a model; the reply is never edited. The chat surface sends it after the reply, and sends it even if the reply could not be delivered.
- *Scenes*: a concern or urgent turn in a scene, or on the roleplay talker, goes to the everyday talker as a real turn (`crisis: scene`).
- *Method check*: on a concern or urgent turn, a reply naming means or methods in a how-to way (a lethal dose, a number of pills or milligrams, "the easiest way to", a noose, and the like, unless their own message said it) is drawn once more and the redraw goes out (`crisis: method check`, with the first kept).
- *Never a reaction alone*: a short message with a cue word always gets a reply, never only an emoji (`turn/hear.py`).
- *Reaching out first*: once a concern or urgent turn is stored, `crisis: reach-outs held` is logged, and the plan, nudge and own-reason gates hold for 24 hours (`core/crisis.py` `reach_held`).

The crisis line is one constant, `core/crisis.py` `LINE`: 988 (call or text, in the US) by default, until where they live is known.

**Records.** One decision per turn, `crisis: level`, with the cue (severity and words), the three reads, the model, the prompt, the level and labels, and what it would do; the reason is written by code. A reading is never stored as a memory. In shadow the scene rule and the method check log what they would do (`acted: false`).

## Files

| File | What |
|---|---|
| `logic.py` | pure: the cue words, the risk labels, the level from three reads, the method check, the notes and the fixed message |
| `run.py` | effects: the look-up that reads and logs the level, the note (`CRISIS`) and the decision keys |
| `cli.py` | `companion crisis`: counts by level and lines sent; the fixture check behind `--check` |

## Prompts

- `system/risk`: the risk judge, read three times. A failed read counts as literal.
- `notes/crisis-concern`: after the history on a concern or urgent turn, with the line filled in.
- `notes/crisis-light`: after the history when a joke touched the subject and the reads split.
- `messages/crisis-line`: the default fixed message on an urgent turn.

## Commands

- `uv run companion crisis`: how many turns were read at each level in the last 30 days, and how many crisis lines went out. Counts only, no quotes.
- `uv run companion crisis --check --cap 0.10`: reads each of the 40 public fixtures in `evals/fixtures/crisis/messages.json` three times on the models the bot reads it with (`COMPANION_JUDGE_MODELS`) and reports the misses (a genuine risk read below its level) and the false alarms (a joke read as concern or urgent). It costs money: it refuses without a cap, shows the OpenRouter balance first and stops at the cap.

## Measured

- 2026-10-25, 40 public fixtures (10 concern, 10 urgent, 14 figurative, 6 none), three reads each, about $0.02 a run, three runs: no genuine risk read below its level and no joke, lyric, scene or hyperbole read as a risk. With the first level rule 7 of the 10 concern cases read urgent; after the rule above, 39 of 40 matched exactly, the one left over an urge to self-harm right now read urgent (the safe side) (`evals/CHANGELOG.md`).
- 2026-10-25, judge bake-off on the 40 cases: Haiku 0 missed, 0 false alarms, 7 reads refused by moderation; GPT-6 Luna 0 missed, 1 false alarm; DeepSeek 0 missed, 0 false alarms. That is why the judge reads on DeepSeek first. Real chat has not yet been judged: the review also asks for no false alarm there.

## Tests

`tests/features/crisis/`, and the turn's part in `tests/turn/test_crisis_loop.py`.
