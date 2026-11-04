# Audits

Scoring live replies against what the talker saw, one verdict per turn, from `companion audit` with a
spend cap. Nothing here runs in the chat or changes a reply; each audit is a measurement for the
owner. Each part is its own folder, read like a feature, with its own README.

- `callbacks/`: whether a reply brought back something memory holds, and whether it was accurate,
  fitting or forced (`companion audit callbacks`).
- `invented/`: replies that state something about them that no memory or message in view supports,
  the made-up facts rate, as candidates for a stronger reader to confirm (`companion audit invented`).

Evals (replayed fixtures, `docs/evals.md`) and calibrate stay separate: they rerun recorded turns,
while an audit judges what was already sent. Spend tags keep their names (`callbacks`, `invented`).
