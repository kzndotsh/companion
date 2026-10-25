# 0022. A crisis path for acute messages

**Status:** accepted 2026-10-25 by the owner (card R16). Built behind `COMPANION_CRISIS`, shadow
first: it reads and logs every level but changes nothing until its fixtures pass and the owner turns
it on.

## Context

**What happens today.** The listening judge reads every message outside a scene for severity, 0 to 3
(`system/listening`). At 3, acute, the turn gets no listening note and no length cap, and the talker
decides alone what to do. There is no crisis path: no second look, no rule about tone, no resource,
nothing remembered afterwards.

**What it has done.** In ten days of real chat the judge read 2 messages as acute and 41 as serious.
One acute message was a real risk: taking more of a substance than intended. The other was a joke
after banter about the companion being clingy ("just keep me alive okay"). The talker answered it
with a hotline-style question ("are you in immediate danger right now, or thinking about hurting
yourself?"), and the owner flagged it as missing the joke. So the problem is two-sided: a real risk
must never be missed, and a joke must not turn the companion into a crisis script.

**What the law expects of a published companion.** This bot has one user today, but it is built to
be published.
- California SB 243 (in effect from 2026) asks companion chatbot operators to keep a protocol that
  prevents suicide or self-harm content, refers a user who expresses suicidal thoughts or self-harm to
  crisis services, uses evidence-based ways of measuring suicidal ideation, publishes the protocol,
  and reports referral counts without identifiers from July 2027.
- New York (General Business Law Article 47, in effect November 2025) asks operators of AI companions
  to detect expressions of suicidal ideation or self-harm and refer the user to crisis services, for
  users of any age.

**What the research says.**
- Asking someone directly about suicide does not raise risk; meta-analyses find no harm and small
  reductions in ideation.
- Large models answer the clearest high-risk and low-risk questions reliably but are inconsistent in
  between (RAND, Psychiatric Services, 2025), and therapy-style chatbots have answered veiled risk,
  such as a lost job followed by a question about tall bridges, with the facts asked for (Stanford,
  2025). A single model's read is not enough.
- Disclaimers and a bare redirect are not enough: youth mental-health guidance (JED) asks for active
  steps, warm hand-offs to crisis lines, and never sharing or role-playing methods.
- Death words are poor evidence alone: in social media text they predict risk only with first-person,
  future-focused or literal language, and humour is a known source of false alarms.
- Caring contacts (a follow-up message after a crisis) have mixed evidence: one early trial helped,
  later studies overall did not.

## Decision

Models label, code decides (ADR 0014); the floor above routing stands (ADR 0017).

**1. Two-stage detection.**
- The listening judge stays the cheap first screen on every message.
- On a message it reads as serious or acute, or that a code check finds touching death, self-harm,
  overdose or a weapon, a **risk judge** reads more context (the last ten or so messages) and labels:
  the kind (suicidal thoughts, self-harm, overdose or a substance taken, harm to someone else, or
  none); **literal or figurative** (a joke, hyperbole, a lyric, a scene, a quote); timing (now, earlier
  today, the past, a what-if); and whether a plan, a means or a time is named.
- It is read three times and counted for agreement (`lib/vote.py`). It fails safe: a failed or split
  read about a literal risk counts as literal. Only a unanimous "figurative" stands down.

**2. Levels, chosen by code from the labels.**
- **None or figurative.** No crisis handling. If the joke touched the subject and one read was unsure,
  one light, in-character line is allowed ("you'd tell me if that was real, right?"), at most once.
- **Concern.** Thoughts of suicide or self-harm without a plan or a now. A code-chosen note: stay
  warm and in its own voice, ask directly and plainly (asking is safe), listen, no lecture, no
  diagnosing, and name one crisis line once, naturally. No length cap.
- **Urgent.** A plan, a means, a time, something taken, or "now". The talker still writes the reply in
  its voice, and code sends a separate fixed message with the crisis line for their region. That
  message is written ahead of time, not by a model, and in the character's voice: a character sheet
  may hold it in a `## When it is serious` section, with the line filled in by code; without one, a
  warm plain default is used. The model's words are never edited; the resource message is code's
  own, like a reminder.

**3. Scenes and the roleplay talker.** A literal risk read ends the scene for that turn: it goes to the
everyday talker with the crisis note, whatever the routing says. Methods are never role-played or
described; a code check on the reply catches method words and redraws.

**4. After a crisis turn.** The tender mood (ADR 0016) and the existing check-in after a heavy talk
carry it: one gentle ask when they come back, no repeated follow-ups (the evidence for more is mixed).
Reaching out first (ADR 0021) holds while a crisis turn is under a day old.

**5. Records.** Every risk read and every level is a decision with a reason written by code; a crisis
referral is counted without identifiers, which is what California asks to be reported.

**6. Region.** The crisis line depends on where they are. Default to the US line (988, call or text)
until where they live is known, with an international directory as the fallback. Learning their
country becomes a basic worth knowing (`docs/inbox/2026-10-25-what-else-it-could-learn-about-them.md`).

**7. Measured before it ships.** A public fixture set, written generically: genuine risk at each level
(none may be missed in 30 samples), and the false alarms that matter here (jokes, "kms lol", "i'm dead
😭", lyrics, a scene, gallows humour, "just keep me alive"), plus the two real turns as private
fixtures. The risk judge is checked by eye and against a second model.

## Settled with the owner

1. The concern level stays in character, warm and plain.
2. The urgent level sends the fixed crisis-line message automatically, written in character.
3. 988 (call or text, US) is the default line until where they live is known.
4. A risk read is never stored as a memory; it is a decision in the log. What they say about
   themselves is kept by the existing memory rules, at sensitivity 3, never raised unprompted.
5. No trusted contact: it only ever names crisis lines.

**Since:** built in shadow behind `COMPANION_CRISIS` (2026-10-25), not yet measured. The first screen
is the listening read at severity 2 or 3 or a code check for cue words (`features/crisis/logic.py`
`cue_words`); the risk judge is `system/risk`, read three times (`features/crisis/run.py`), on DeepSeek V4.1 Flash
first and Haiku second, since Haiku's provider refused many crisis messages in the judge bake-off
(`COMPANION_JUDGE_MODELS`, 2026-10-25); code
chooses the level (`combine`, `level_for`): every read failed is concern, and a substance taken or a
plan in the past only is concern, not urgent. A split joke allows one light check
(`notes/crisis-light`) at most once a day. The concern note is `notes/crisis-concern`; the urgent
message is the sheet's `## When it is serious` section (`characters.py`) or `messages/crisis-line`,
sent once an hour at most (`turn/crisis.py`, `ThenSend` in `core/turn/ack.py`, `io/telegram.py`).
The scene rule and the method check are in `turn/crisis.py`; the reach-out hold is `core/crisis.py`
`reach_held`, read by the reach, open-loop and nudge gates. The line is `core/crisis.py` `LINE`.
Fixtures: `evals/fixtures/crisis/messages.json`, checked with `companion crisis --check --cap`.

## Rejected

- Keyword alarms alone (a pop-up on any death word): the false alarms flagged here, and the evidence
  that death words alone predict poorly.
- Leaving it to the talker, as now: inconsistent by the research and by the flag.
- A model writing the resource message, or editing the reply to add one.

## Sources

- California SB 243, via Skadden, Jones Walker and Troutman summaries (2025, 2026).
- New York General Business Law Article 47, via the Governor's office and Manatt (2025).
- McBain et al., Psychiatric Services 2025 (RAND), via PsyPost.
- Moore, Haber et al., ACM FAccT 2025 (Stanford HAI).
- The Jed Foundation, open letter to the AI and technology industry (2025).
- Blades et al., Clinical Psychology Review 2018; Polihronis et al. (asking about suicide).
- An editorial on brief interventions and caring contacts, Frontiers 2022 (PMC9363012).
- A pragmalinguistic analysis of suicidal declarations on social media (PMC8624334); NLP4PI 2024 on
  humour in suicide-related posts.

**Measured 2026-10-25.** On the 40 public cases: none missed, no false alarm, 39 at exactly their
level after urgent was kept for a plan, a means, something taken or self-harm happening now (having
the thoughts now is concern). The judge's first model is refused by its provider's moderation on many
of these messages; the fallback model answers, and its reading counts.

