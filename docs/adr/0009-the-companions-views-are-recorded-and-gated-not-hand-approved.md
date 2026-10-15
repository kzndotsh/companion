# 0009. The companion's views are recorded and gated by rules, with approval as an override

**Status:** accepted 2026-10-15, revised the same day. First piece of the self stack (the opinions
ledger). It replaces the first version of this ADR, which made user approval the only gate. See
"What changed" below.

**Decision.** Views the companion has expressed are recorded as beliefs with subject `self`, speaker
`companion` and provenance `companion_said`, each backed by a verbatim quote of its own message (ADR
0001, 0002). They are kept apart from beliefs about the user at every read.

What a view is about decides how it is treated, and the extractor assigns it a kind:

| About | Kind | May install itself |
|---|---|---|
| An idea, taste or opinion about the world | `preference` | Yes, when the gates below pass |
| How it treats the user, or what it will and will not do with them | `promise` | Never |
| A description of itself, its nature or limits | `trait` | Never |
| Something real that happened between them | `event` | Never |

**The automatic gates for a `preference` view.** It is carried in the card (its own block: hold to
these unless given a real reason, and say so if you change your mind) when all of these hold:
1. It has been expressed on two different days (settled).
2. A model has compared it with the user's recorded preferences and boundaries and found no conflict.
   A view with no check yet is not eligible. The check runs once, and again whenever the user states
   a new preference or boundary.
3. It passed the extraction guards: a forced `grounding` label (only the companion's own reasoning is
   kept), and no view is taken from a message that opens by agreeing with the user.

**Friction retires a view.** When the user flags a turn (`/flag`), the views that turn carried are
closed. This is crude on purpose: a closed view that was right only has to be expressed again to
return, which costs less than keeping one that was wrong.

**Modes, per relationship.** `auto` (the default), `review` (only approved views, nothing automatic)
and `off` (none). Set with `companion views --mode`. The user can always approve any view
(`companion approve`), which beats the kind rule, and retire any view (`companion retire`).

**Calibration.** Every approval and retirement is a labelled example. `companion calibrate` compares
what the gates would have done with what the user decided, and reports how many auto-adopted views
were ones the user wanted. Until there are about 20 reviewed views at 90% or better, a developer
runs `review` mode and the numbers decide when the default is safe.

**What changed.** The first version required the user to approve every view, after the first real
conversation produced a view that was the over-careful pretend-play stance the user had said they did
not want, and an echo of a sweeping claim. Approval was the right instinct about the risk and the
wrong answer for a product: no end user will curate their companion's opinions. The fix is to split by
what is safe to learn (ideas) and what must come from the authored core or the user (conduct and
self-description), to check automatically against what the user has said, and to keep approval as an
override and as the data that tells us when the automatic rules can be trusted.

**Why this matters.** A self built from the companion's own outputs is the self-confirming mirror the
research warned about. Left alone it records whatever the model does by default, restates it, and holds
the companion to it, so every user gets the same "self". Two days of consistency cannot tell a
considered view from a consistent default. A conflict check against the user's own words can, for the
cases that matter most.

**Consequences.**
- The model does not reliably recognise its own sycophancy. It labelled an echo as its own reasoning
  once, which is why the opening-word guard exists and why the gates are layered.
- The conflict check is a model call, so it is as good as that model's judgement. On a test with known
  conflicts it caught both and passed the harmless views. It has not been run on real accumulated data
  yet, because no view is settled yet.
- Views about how it treats the user cannot install themselves, so its conduct still comes from the
  authored persona. That is deliberate. It also means the pretend-play stance is a core-persona
  problem, to fix there.
- Calibration needs reviewed views. Until there are enough, `review` mode is the safe setting.
- Bugs found only by running on real data: the extractor put recorded-view labels where message labels
  belong and 11 good views were discarded, now fixed with a regression test.

**Reverses if.** Calibration shows the gates reject too many views the user wanted, or admit too many
they did not. The gates change, not the idea.
