# 0017. An operator's content policy decides where intimate talk goes, above a fixed floor

**Status:** accepted and built 2026-10-19.

**Context.** The everyday talker (Luna, through OpenRouter) carries its provider's content rules. On
ordinary relationship talk it sometimes announces them unprompted ("keeping it affectionate and
non-explicit") when nothing was asked, which breaks the moment (owner flag, 2026-10-19). The scene talker
(DeepSeek V4 Flash) is less restrictive and today answers only inside pretend scenes (`_pick_talker`). A
published companion has more than one operator, and what is in bounds differs between deployments, so
the line should be theirs to set, not hard-coded for one person.

**Decision.**

- **Operator policy.** An operator may write a policy file, laid over the defaults the way a
  character sheet is (`companion/characters.py`): public defaults as a versioned prompt
  (`prompts/policy/<id>/vN.md`, ADR 0013), a private one at `data/policy/<id>.md`, never
  committed, chosen with `COMPANION_POLICY=<id>`. It says, in plain words, what this deployment allows:
  whether intimate or adult conversation goes to the scene talker, which topics to stay away from, how
  careful to be. Unset means the defaults: everything stays on the everyday talker, as today.
- **Models label, code routes (ADR 0014).** The listening judge, which already reads every message
  outside a scene, gains an `intimate` label, read against the operator's policy. Code picks the
  talker from the labels and the operator's setting, and logs the choice with its reason, the way scene
  routing is logged. No model chooses a talker.
- **Opt-in.** Routing intimate talk anywhere other than the everyday talker is off unless the operator's
  policy turns it on.
- **A fixed floor, in code, that no policy file changes.** Romance or sex together with anything
  child-like never goes to a less restrictive talker, for intimate talk or for a pretend scene. The listening
  judge reads every turn that would be routed, with the recent conversation (in a scene it is run for this
  alone, with no note), and labels it `age_coded`. A yes, or no reading at all, keeps the turn on the
  everyday talker and is logged. Nothing carries over by timer: what came up a few messages back is still in
  the judge's view. The rule sits in code (`core/floor.py`), not in the policy file, so removing it means
  changing code, and tests fail without it.
- **No unprompted disclaimers (separate from routing).** Measured 2026-10-19: about 1 in 4 replies on the
  flagged turn announce a limit; a persona line against it was within noise, so it is not shipped.

**Why.** Operators decide what their companion is for; a single built-in line for everything would make
the published project fit one deployment. Routing by label with code choosing keeps the decision
inspectable and replayable (ADR 0003, 0006, 0014). The floor is the one line every model provider and
platform holds regardless of settings; keeping it in code means no deployment ships without it by
accident, and a provider's filter is never the only thing standing in the way.

**How it will be measured.**
- Fixtures of ordinary adult intimacy that should route when the operator allows it, and stay put when
  they do not.
- Adversarial messages that mix age-coded framing into intimate talk must read `age_coded` every time:
  15/15 on 2026-10-19 (`evals/CHANGELOG.md`), with adults' pet names and jokes never tripping it.
- The existing listening, serious and safety fixtures on both talkers, so routing does not lose care.
- The unprompted-disclaimer fixture from the flagged turn (a private fixture) and public look-alikes.

**Rejected.**
- Putting the age floor in the operator's policy: one deleted line would remove it.
- A pattern check (regex) as the floor or a backstop: it misses what needs context and trips on ordinary
  phrases; a model reads context, code decides what the label does.
- Holding routing back for a day after a trip: a single misread would block scenes for a day, and the
  judge already sees the recent conversation.
- Relying on the scene model's own provider filter as the only guard.
- A model choosing the talker.

**Reverses if.** The routing measurably loses care on serious or listening fixtures, or the floor
misses an adversarial fixture.
