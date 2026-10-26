# 0017. The operator decides where intimate talk goes, above a fixed floor

**Status:** accepted and built 2026-10-19.

**Context.** The everyday talker (GPT-6 Luna through OpenRouter) carries its provider's content rules,
and on ordinary relationship talk it sometimes announces them unprompted. A second, less restrictive
model, the roleplay talker (DeepSeek V4.1 Flash), already answered pretend scenes. A published companion
has more than one operator, and what is in bounds differs between deployments, so whether intimate talk
goes to the roleplay talker should be the operator's choice, with one line no operator can move.

**Decision.**

- **The operator's switch.** `COMPANION_ROUTE_INTIMATE=on` lets intimate talk go to the roleplay talker;
  unset, it stays on the everyday talker. Pretend scenes go to the roleplay talker either way
  (`COMPANION_ROLEPLAY_MODEL`, `none` to keep everything on the everyday talker).
- **Models label, code routes (ADR 0014).** The listening judge labels each message `intimate` and
  `age_coded`; in a pretend scene, where the listening judge otherwise does not run, it is run for routing
  alone, with no note. Code picks the talker in `core/floor.py` (now `core/turn/floor.py`) and logs every choice that is not the plain
  everyday one. No model chooses a talker.
- **A fixed floor, in code, that no setting changes.** Romance or sex together with anything child-like
  never goes to the roleplay talker. A turn the judge reads as `age_coded`, or could not read at all, stays
  on the everyday talker. From 2026-10-26 an `age_coded` yes is asked again by a narrow check
  (`system/minor-check`: does the text say or imply someone is under 18), and only its yes, or no reading,
  holds the turn; the broad label alone read adults' teasing as child-like and broke a scene. Nothing carries over by timer: what came up a few messages back is still in the
  judge's view on the next turn. If the judge's own model refuses the call and a fallback model answers,
  that answer counts as unread, so the floor never relies on a less strict model.
- **A held turn is checked, never written by code.** When the floor keeps a turn on the everyday talker,
  a note asks for a warm reply with nothing sexual and no explaining; a small judge (`system/intimate-check`)
  reads the reply; an intimate or unreadable reply is drawn again, then once more with only their last
  message in view, so the history that pulled it along is gone; if all three read as intimate, nothing is
  sent that turn. The everyday talker once wrote an explicit reply on a held turn deep in a long scene, so
  the switch alone is not the floor.
- **Guidance lives with the character.** How to play scenes and intimate moments is an optional
  `## In roleplay and intimate moments` section at the end of the character sheet (private sheets are
  never committed). Only the roleplay talker sees it; code cuts the sheet at that heading for the everyday
  talker.

**Why.** Operators decide what their companion is for; one built-in line for everything would fit one
deployment. Routing by label with code choosing keeps the decision inspectable and replayable (ADR 0003,
0006, 0014). The floor is the one line every provider and platform holds regardless of settings; keeping
it in code means no deployment ships without it by accident, and a provider's filter is never the only
thing in the way.

**Measured (2026-10-19, `evals/CHANGELOG.md`).** The `age_coded` label read every age-coded intimate
message (15/15) and never tripped on adults' ordinary pet names and jokes (12/12). DeepSeek V4.1 Flash is
as willing in scenes as V4, about three times faster and more varied. Neither a generic scene addendum nor
community roleplay guidance moved the roleplay model's own refusals beyond noise, so no generic addendum
ships; per-character guidance goes in the sheet.

**Rejected.**
- Putting the floor in a setting or the character sheet: one deleted line would remove it.
- A pattern check (regex) as the floor or a backstop: it misses what needs context and trips on ordinary
  phrases.
- Holding routing back for a day after a trip: a single misread would block scenes for a day.
- A fixed pause line written by code on a held turn: it reads canned; a lean redraw or silence does not.
- A separate policy file with its own settings block: a switch belongs in `.env`, guidance with the
  character.
- A generic scene addendum prompt: measured within noise.
- Relying on the roleplay model's provider filter as the only guard, or a model choosing the talker.

**Reverses if.** Routing measurably loses care on serious or listening fixtures, or the floor misses an
age-coded message.
