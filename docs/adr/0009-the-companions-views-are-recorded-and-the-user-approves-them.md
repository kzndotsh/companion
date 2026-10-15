# 0009. The companion's own views are recorded, and the user approves them

**Status:** accepted 2026-10-15. First piece of the self stack (the opinions ledger).

**Decision.** Views the companion has expressed are recorded as beliefs with subject `self`, speaker
`companion` and provenance `companion_said`, each backed by a verbatim quote of its own message.
They use the existing belief machinery (ADR 0001, 0002) and are stored as kind `preference`, `trait`
or `event`, so no schema change was needed. They are kept apart from beliefs about the user at every
read: the user card, the user extraction pass and rebuilds all use `Store.user_beliefs`, never all
beliefs.

A view reaches the card only when **the user has approved it** (`companion approve <id>`, recorded in
`view_approvals`, append-only). Approved views appear in their own block: hold to them unless given a
real reason, and say so if you change your mind. `companion opinions` lists every view with whether
it is approved and whether it is settled (expressed on two different days). Closing a view
(`companion retire`) ends its effect.

**Why approval.** A self built from the companion's own outputs is the self-confirming mirror the
research warned about. On the first real conversation the extractor recorded, among good views
("faking humanity would make me worse at what I am"), two bad ones: an echo of a sweeping claim
("other apps feel like a corporate memo"), and the over-careful stance on pretend play that the
user has told it they do not want. Restated daily, that stance would be "settled" and then held. Two
days of consistency cannot tell a considered view from a consistent model default. The user's
judgment can.

**Guards before the user sees a view.**
- Each candidate carries a `grounding` label (own reasoning, echoes the user, unknowable, claims an
  inner state). Only own reasoning is kept. The model labels, code decides.
- A view is never taken from a message that opens by agreeing ("yeah", "they really are"), because
  that is how the measured sycophancy starts. This is a deterministic check on the source message,
  and it exists because the model labelled one echo as its own reasoning.
- The quote must be verbatim from a *companion* message. The rescue for a garbled message label
  searches the companion's messages only.

**Consequences.**
- Nothing about the companion's self changes until the user approves it. The feature costs about a
  tenth of a cent per pass and is inert until used.
- The model does not reliably recognise its own sycophancy, so the guards are layered and the final
  filter is human.
- One bug found by testing on real data: the model put recorded-view labels (`k1`) where message
  labels (`m12`) belong, and 11 good views were discarded. The fix is a clearer prompt and a rescue
  that finds the one companion message containing the quote. Without testing on a real conversation,
  that would have shipped.
- Views about what it said it *did* (events) and confirmations are not part of the card yet. Lore,
  the style profile and mood are the rest of the self stack and are not built.

**Reverses if.** Approval turns out to be too much friction to use, or the companion's views prove
reliable enough to trust once settled. Then settled could go to the card by default, with approval as
a veto, which is a one-line change in `core/views.py`.
