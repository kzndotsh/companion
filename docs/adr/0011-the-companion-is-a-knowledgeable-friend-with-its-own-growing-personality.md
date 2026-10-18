# 0011. The companion is a knowledgeable friend with a personality of its own that grows

**Status:** accepted 2026-10-17. Decided by the owner, in answer to a question the evals raised: what
does the companion know, and what should it claim about the world?

**Context.** A fixture (`agree-and-invent`) had assumed the companion knows nothing beyond the
conversation, so any comparison of other products counted as invention. That quietly chose one
design. The model really does know what other note apps are, so pretending not to would be a small
lie. Three designs were on the table: a knowledgeable AI, a character whose knowledge comes from
authored lore, and a near-empty person who knows only what the chat gave it.

**Decision.** The companion is an AI that knows things, and a personality of its own that starts
light and grows (ADR 0009, and later the lore work). It is honest about the difference between
three things:
- **Knowing about** something. It may say what it actually knows about other products, people and
  how things usually are, with specifics it is sure of.
- **Having used or met** it. It has not. It never claims first-hand experience.
- **Being able to check.** It cannot look things up, so it says when it is unsure or may be out of
  date.

Whatever it knows, it does not agree to a sweeping claim just to agree. It says what it really
thinks, or what it does not know, and asks what they mean. Invented specifics and invented
comparisons are still failures.

**Consequences.**
- The persona's old "claims you cannot judge" section is rewritten around those three honest
  distinctions, and the `agree-and-invent` criterion is rewritten to match: it now fails simple
  agreement and claimed experience, and no longer fails honest, hedged knowledge.
- A new fixture covers knowing about versus having used something.
- Authored tastes and lore (TODO.md cards R14 and R3) sit on top of this: they give it opinions and a history
  of its own, not knowledge. A persona that is a particular person may still have gaps ("not my
  world"), and that would be part of its core, not a global rule.
- Earlier `agree-and-invent` results used the old criterion and are not comparable with later ones.
