# 0009. The companion's views are recorded and gated by rules, with approval as an override

**Status:** accepted 2026-10-15, revised the same day. First piece of the self stack (the opinions
ledger). It replaces a first version that made user approval the only gate (see Context).

**Context.** The first version required the user to approve every view. The first real conversation
produced a view that was an over-careful pretend-play stance the user had said they did not want, and
an echo of a sweeping claim. Approval was the right instinct about the risk and the wrong answer for a
product: no end user will curate their companion's opinions.

A self built from the companion's own outputs is also a self-confirming mirror. Left alone it records
whatever the model does by default, restates it, and holds the companion to it, so every user gets the
same "self". Two days of consistency cannot tell a considered view from a consistent default. A conflict
check against the user's own words can, for the cases that matter most.

**Decision.**

- **Views are beliefs about itself.** A view the companion has expressed is recorded with subject
  `self`, speaker `companion` and provenance `companion_said`, backed by a verbatim quote of its own
  message (ADR 0001, 0002). Views are kept apart from beliefs about the user at every read.
- **The kind decides who may install it.** The extractor gives each view a kind:

  | About | Kind | May install itself |
  |---|---|---|
  | An idea, taste or opinion about the world | `preference` | Yes, when the gates pass |
  | How it treats the user, or what it will and will not do with them | `promise` | Never |
  | A description of itself, its nature or limits | `trait` | Never |
  | Something real that happened between them | `event` | Never |

- **Three gates for a `preference`.** It enters the card (its own block: hold to these unless given a
  real reason, and say so if you change your mind) when all of these hold:
  1. It was expressed on two different days (settled).
  2. A model compared it with the user's recorded preferences and boundaries and found no conflict. A
     view with no check yet is not eligible. The check runs once, and again whenever the user states a
     new preference or boundary.
  3. It passed the extraction guards: a forced `grounding` label (only the companion's own reasoning is
     kept), and no view is taken from a message that opens by agreeing with the user.
- **Friction retires a view.** When the user flags a turn (`/flag`), the views that turn carried are
  closed. This is crude on purpose: a closed view that was right only has to be expressed again to
  return, which costs less than keeping one that was wrong.
- **Modes, per relationship.** `auto` (the default), `review` (only approved views) and `off`. Set with
  `companion views --mode`. The user can approve any view (`companion approve`), which beats the kind
  rule, and retire any view (`companion retire`).
- **Calibration.** Every approval and retirement is a labelled example. `companion calibrate` compares
  what the gates would have done with what the user decided. Until there are about 20 reviewed views at
  90% or better, a developer runs `review` mode and the numbers decide when the default is safe.

**Why.** Split by what is safe to learn (ideas) and what must come from the authored core or the user
(conduct and self-description). Check automatically against what the user has said. Keep approval as an
override and as the data that tells us when the automatic rules can be trusted.

**Measured (at the time of writing).**
- The model does not reliably recognise its own sycophancy. It once labelled an echo as its own
  reasoning, which is why the opening-word guard exists and why the gates are layered.
- The conflict check is a model call, so it is only as good as that model. On a test with known
  conflicts it caught both and passed the harmless views. It had not yet run on real accumulated data,
  because no view was settled.
- Running on real data found a bug: the extractor put recorded-view labels where message labels belong
  and 11 good views were discarded. Fixed, with a regression test.

**Consequences.**
- Views about how it treats the user cannot install themselves, so its conduct comes from the authored
  persona. That is deliberate. It also means a pretend-play stance is a persona problem, to fix there.
- Calibration needs reviewed views. Until there are enough, `review` is the safe setting.

**Rejected.** (added 2026-10-19 from the context above, not recorded at the time) Approval as the only gate (no end user will do it). Letting every kind install itself.
Settledness alone as the test (consistency is not consideration).

**Since:** the gates and modes are as built (`core/views.py`: two days, `preference` only, at most 8
views carried). The calibration threshold has not yet been reached; the gates stay a card on the board
(TODO.md, "calibrating the view gates").

**Reverses if.** Calibration shows the gates reject too many views the user wanted, or admit too many
they did not. The gates change, not the idea.
