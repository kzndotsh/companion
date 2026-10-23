# How a reply is made

The reply path's own behaviour, stage by stage, beyond what each feature's README says. The stages
live in `turn/` (`hear`, `route`, `notes`, `assemble`, `talk`, `beside`, `persist`; `fast.py` is
the driver, `handle(convo, ...)`).

- Each message outside a scene is read for how serious it is before the reply, and code adds a
  listening note (`core/turn/listening.py`). `COMPANION_LISTEN=off` turns it off. Acute messages (severity
  3) get no note and there is no crisis path yet. The same judge labels a message rude to the
  companion (a one-turn note for a cool reply) and a request to remember something; then a small model
  looks the topic up across every belief and the finds ride that turn's system block
  (`core/recall.py`). Sensitive (held) memories are in the card only on turns rated severity 1 or
  more; the beliefs the card has no room for are logged once per turn. A one-day moment of daily life
  (an event labelled daily and surface by the memory map), and a personal event on a given day, leave
  the card a week after last mentioned; they stay in memory.
- Coming back 3 hours or more after a talk that turned serious (severity 2 in its last 12 hours),
  the next ordinary message gets one note to ask gently how they are now (`notes/check-in`), once per
  heavy talk.
- A mood that carries (ADR 0016, `features/mood/logic.py`): each message adds effects to cozy, tender or
  playful in an append-only table, the mood is worked out from them when read, and only what the user
  did can move it (no source for silence, goodbyes, gaps or failed calls). `COMPANION_MOOD` is shadow,
  on or off; `uv run companion mood --replay 7` rebuilds it over past messages from the same rules.
- Which talker answers is chosen in code (`core/turn/floor.py`, ADR 0017): the roleplay talker for a
  pretend scene, or for intimate talk when `COMPANION_ROUTE_INTIMATE=on` once it is under way (their
  message before was intimate too, or this one is explicit by `system/explicit-lead`; a first flirty
  line gets the everyday talker), unless the listening judge reads the turn as age-coded or could not
  read it (a fallback model's reading counts as unread). That floor is code, not a setting. A held
  turn gets a note, its reply is read by an intimate check and redrawn (the last draw sees only their
  message), and if all read intimate nothing is sent; no reply is written by code. The roleplay talker
  also sees the character sheet's `## In roleplay and intimate moments` section; the everyday one
  never does. A `## Scene reminder` at the end of that section is sent after the history on roleplay
  turns (`TalkerRequest.tail`), where it weighs most; its words live in the private sheet. When they
  push the flirting or the scene back, even jokingly, a small judge says so (`system/brush-off`, asked
  only of a turn the roleplay talker would answer) and that turn goes to the everyday talker with
  `notes/brush-off`; the floor still comes first. "Scene" means only a pretend scene in progress (the
  frame judge's label); a scene ends when they step out of it or come back after two hours or more
  (`core/frames.py` `SCENE_GAP`).
- Replies are checked before they are sent (`core/recheck.py`): on an ordinary turn (not serious,
  not a scene) an em dash, an AI disclaimer nobody asked for, the clock line or a tag copied from the
  system block, the stock "that sounds X, especially when" line, the stage direction "a beat" and
  markdown that shows raw (outside scenes), by code, and a joke bolted onto an ordinary message by the
  quip judge; in a scene or on a serious turn only the code checks. On a fail the same model is asked
  once more (twice if the redraw still has an em dash) and the last reply goes out whatever it is; the
  first is kept in the decision detail. Nothing is ever edited, and an empty reply is drawn once more
  instead of a silent turn. `COMPANION_RESAMPLE=off` turns it off.
- When one of its last two replies owned a slip ("my bad", "I got that wrong"; `core/turn/ownup.py`,
  sympathy is not one), the next turn outside a scene gets `notes/owned-it` after the history, as a
  system message: that was enough, no more apologies or self-blame. In the system block it moved
  nothing; after the history it did, but only early in a run of apologies (measured). Text sent after
  the history is logged with the turn (`tail: sent after the history`) so replay rebuilds it.
- A talker that errors is answered by its fallback model at once, and one still silent after 10 s
  has the fallback asked too, the first answer sent (`models/fallback.py` `TalkerFallback`, J21). The
  reply carries the model that wrote it, and every check runs on it as usual. Talker calls time out at
  25 s.
