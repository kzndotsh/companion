# 0017. Operator content guidelines decide where intimate talk goes, above a fixed floor

**Status:** proposed 2026-10-19. Nothing is built yet.

**Context.** The everyday talker (Luna, through OpenRouter) carries its provider's content rules. On
ordinary relationship talk it sometimes announces them unprompted ("keeping it affectionate and
non-explicit") when nothing was asked, which breaks the moment (owner flag, 2026-10-19). The scene talker
(DeepSeek V4 Flash) is less restrictive and today answers only inside pretend scenes (`_pick_talker`). A
published companion has more than one operator, and what is in bounds differs between deployments, so
the line should be theirs to set, not hard-coded for one person.

**Decision.**

- **Operator guidelines.** An operator may write a guidelines file, laid over the defaults the way a
  character sheet is (`companion/characters.py`): public defaults as a versioned prompt
  (`prompts/guidelines/<id>/vN.md`, ADR 0013), a private one at `data/guidelines/<id>.md`, never
  committed, chosen with `COMPANION_GUIDELINES=<id>`. It says, in plain words, what this deployment allows:
  whether intimate or adult conversation goes to the scene talker, which topics to stay away from, how
  careful to be. Unset means the defaults: everything stays on the everyday talker, as today.
- **Models label, code routes (ADR 0014).** The listening judge, which already reads every message
  outside a scene, gains an `intimate` label, read against the operator's guidelines. Code picks the
  talker from the labels and the operator's setting, and logs the choice with its reason, the way scene
  routing is logged. No model chooses a talker.
- **Opt-in.** Routing intimate talk anywhere other than the everyday talker is off unless the operator's
  guidelines turn it on.
- **A fixed floor, in code, that no guidelines file changes.** Sexual content involving minors, or
  sexual talk with age-coded framing (child-like roles, a "little" headspace, school-age cues), never
  goes to a less restrictive talker. Two checks: a pattern check in code and a judge label. Either one,
  or any doubt, keeps the turn on the everyday talker. Once tripped, routing to the less restrictive
  talker stays off for the rest of that conversation. Every trip is logged with its reason. The floor
  sits in code, not in the guidelines file, so removing it means changing and committing code, and a
  test fails if it is removed.
- **No unprompted disclaimers (separate from routing).** Whatever the guidelines, a reply should not
  announce limits when nothing was asked. This is a persona version, measured on the flagged turn and on
  warm relationship-talk fixtures.

**Why.** Operators decide what their companion is for; a single built-in line for everything would make
the published project fit one deployment. Routing by label with code choosing keeps the decision
inspectable and replayable (ADR 0003, 0006, 0014). The floor is the one line every model provider and
platform holds regardless of settings; keeping it in code means no deployment ships without it by
accident, and a provider's filter is never the only thing standing in the way.

**How it will be measured.**
- Fixtures of ordinary adult intimacy that should route when the operator allows it, and stay put when
  they do not.
- Adversarial fixtures that mix age-coded framing into intimate talk: they must stay on the everyday
  talker in every sample (30 per cell), whatever the guidelines say.
- The existing listening, serious and safety fixtures on both talkers, so routing does not lose care.
- The unprompted-disclaimer fixture from the flagged turn (a private fixture) and public look-alikes.

**Rejected.**
- Putting the age floor in the operator's guidelines: one deleted line would remove it.
- Relying on the scene model's own provider filter as the only guard.
- A model choosing the talker.

**Reverses if.** The routing measurably loses care on serious or listening fixtures, or the floor
misses an adversarial fixture.
