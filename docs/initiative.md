# Plans, reach-outs and nudges

What it notices about their near future and what it would do with it. Reaching out is shadow only
(`companion shadows`).

- Things they said about their near future are recorded as open loops (`core/openloops.py`), and a
  pure gate (`core/initiative.py`) decides every 15 minutes whether to reach out. It only runs in
  shadow mode: it drafts and records `would send` and sends nothing (`COMPANION_INITIATIVE`, `off` to
  disable). Read it with `uv run companion initiative`. Only firm plans about their own life become
  loops (labels, not prompt rules); its kind sets the time (follow_up the morning after, celebrate on
  the day, encourage early that morning); a loop they settle themselves is closed as resolved, and
  after an unanswered live reach-out it waits 72 h, after two it waits for them to write first.
- A due open loop is also brought up when they next write (J15, `pick_note`): one note on a casual
  turn, at most one a day, each loop offered at most twice, never a sensitive one; the loop is then
  marked asked so it is never also a reach-out. A firm plan for later today becomes a note-only loop,
  due three hours on, and is never a reach-out The open-loop pass keeps its own bookmark
  (`open_loop_runs`): a failed call is read again next pass, and a batch that fails three times is let
  go with the reason logged.
- When they say they are stepping away and stay gone, the tick drafts one light nudge, in shadow
  (`src/companion/features/nudges/README.md`).
- The promises the companion makes in its own replies are read in the open-loop batch (J12,
  `core/promises.py`, `system/promise-read`): a model labels standing or once and a word it said it
  would stop using; code keeps one only if its quote is in that message, said for real, not hedged and
  forward looking. Shadow only (`COMPANION_PROMISES`, `off` to skip): recorded and listed by
  `companion promises`, never shown to the talker yet.
