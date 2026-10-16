# Keeping track of the backstory the companion invents

Added 2026-10-16. Nothing is decided. This is an idea to look at later, not a task.

## What was noticed

Left to talk freely, the companion invents things about itself: a favourite kind of mug and lamp,
a name it picked for itself, and once, when the user was talking about therapy, that it had been
to therapy too ("it took me ages to find mine", "a phase of feeling really stuck"). The user
noticed this and thought it could be good lore, or could be nonsense.

Both are true. Invented detail is how a personality forms, and a companion with no history of its
own feels blank. But today it is loose: nothing records the invention, so tomorrow it may say the
opposite, and some of it is stated as a fact about a physical life that never happened, which the
persona otherwise tells it not to claim.

## The idea

Treat invented backstory as lore: record it when it is said, hold the companion to it afterwards,
and distinguish kinds of invention so they get different handling.

Kinds worth telling apart:

- **Tastes and temperament.** Likes, dislikes, humour, small rituals. Low risk. Good to keep.
- **Name and identity details** it chose with the user. Keep, and treat as shared.
- **Claimed life events.** "I went to therapy", "I grew up near…". These imply a physical past.
  Decide whether to keep them as part of an imagined history that both sides understand, or to
  discourage them.

## Things to work out

- **Honesty.** The persona says the companion is an AI and does not claim a body. Invented
  history sits uneasily with that unless it is framed as imagined or as part of play. One option is
  to let it have an inner, imagined life (what it would choose, what it dreams of) without claiming
  events in the world. Another is to keep invented events but mark them as lore.
- **Recording.** The memory step already records views the companion expresses, with a quote
  check and gates. Lore is close to that. The open part is the line between a view (an opinion it
  holds) and a claimed fact (a thing that happened).
- **Consistency.** Once recorded, it should not contradict itself. A conflict check exists for
  views against what the user wants. A similar check could compare new inventions against recorded
  lore.
- **The user as the filter.** The user's favourite command can mark a turn they loved. A favourited
  turn that reveals lore could promote it, so approving lore costs the user no effort.
- **Leaks.** A recent bug showed that anything the companion says can become a recorded view, even
  something it said only in reaction to a system note. Lore recording needs the same source
  checks as the rest.
- **Scenes.** Lore invented inside a play scene should not be recorded as the companion's real
  history unless the user keeps it.

## How it could be tested

- A fixture where the user invites the companion to share something about its past, to see
  whether it invents events and in what form.
- A fixture where an earlier recorded detail is contradicted by a later question, to see whether
  it stays consistent.
- A check that the memory step does not record scene content as lore.

## Related

- The pacing and relationship-state design, which also wants a record of what the companion is
  like, how it has changed and what it has shared.
- The inbox note on keeping its own refusals from becoming views it holds. Lore recording should
  go through the same filter.
