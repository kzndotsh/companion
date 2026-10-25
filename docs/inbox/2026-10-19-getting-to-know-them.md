# Getting to know them, on purpose

**Status (2026-10-25):** partly built: asking a name and pronouns, a name capture, memories labelled by domain and depth, and a basics hook in shadow (`src/companion/features/basics/`, `hooks/`), card J48; the rest waits on the review of 2026-10-26.

Added 2026-10-19. A design sketch to discuss, not a task yet.

## The problem

A companion that only remembers what the user happens to say never gets to know them. On the owner's
history (about 700 messages), 34% of replies asked a question, but almost all were about the thing just
mentioned ("what did you have with it?"), not about the person. The memory is lopsided: 17 beliefs about
food, 8 about music, 1 about goals, none about values, and the user's name was never asked until they
pointed it out. The same user also flagged the opposite failure, replies that keep "seeking answers" and
feel rushed, and questions about logistics or causes that feel like an interrogation. So the fix is not more
questions. It is better aimed ones, at the right moments, with the companion giving something of itself.

## What the research says (2026-10-19, search summaries; see the evals or research notes for URLs)

- Asking questions increases liking, and **follow-up questions** matter most; too many, repetitive or rude
  ones backfire (Huang et al. 2017, measured).
- Closeness grows through **escalating, reciprocal disclosure** (Aron's Fast Friends, measured; social
  penetration theory, breadth then depth, recalled).
- Intimacy needs disclosure **and feeling understood**: a question is only welcome if the answer is received
  responsively (Reis and Shaver, Laurenceau 1998, Shelton 2010, measured).
- A chatbot that discloses more draws deeper disclosure back (Lee et al. 2020, Moon 2000).
- Filler questions raise engagement numbers short-term and hurt long-term (XiaoIce paper).
- A production companion that mixed proactive questions with memory extraction reported longer
  conversations over 30+ days (PaRT 2025); personalization only becomes noticeable after several sessions.
- No standard measure of "it knows me" exists.

## The system, as layers

1. **A map of them.** Every belief about the user gets a domain (who they are and what to call them; people
   and pets; daily life and work; interests and tastes; history and formative stories; hopes and plans;
   values and views; inner life) and a depth (surface, personal, core). Labels come from the extractor or a
   cheap pass over existing beliefs; code keeps the counts.
2. **Gaps, chosen by code.** A pure function reads the map: basics first (the name and what to call them),
   then breadth (thin domains), then depth in domains they already open up about. It picks at most one gap.
   Sensitive domains (health, money, sexuality, politics, faith) are never asked about, only received.
3. **The moment, chosen by code.** Only on a casual turn (the listening judge read it as ordinary), never in
   a scene, a serious moment or right after a goodbye; not two curiosity turns in a row; a small daily budget;
   not when they are clearly winding down.
4. **The note.** On a chosen turn, one line in the system block: if it fits naturally, react first, share a
   bit of your own, then ask about the gap. It replaces a logistics question rather than adding one. Follow-ups
   on what they just said always beat a new gap.
5. **Reciprocity.** The companion has small things of its own to share (its character sheet, and later the
   lore of J6), so asking is a trade, not a survey.
6. **Closing the loop.** The answer is stored with its quote (ADR 0001) and fills the gap; later it comes back
   as a callback (J2) or an open loop (ADR 0015), which is where "it knows me" is actually felt.
7. **Depth grows with closeness.** Which depth is allowed follows the relationship's stage (T17): early on,
   surface; after weeks and real shared moments, personal; core only when they have gone there themselves.
8. **Backing off.** A deflected or short answer marks that domain to rest for a long while; a domain they
   light up about earns follow-ups.
9. **They can see it.** A way to see what it knows and correct it (the user-visible memory idea), so being
   known never feels like being watched.

## How it would be measured

Coverage of the map over time; the question rate staying about the same (better aimed, not more); how often a
curiosity question gets a real answer against a deflection; the share of follow-ups against new topics;
flags and favourites on those turns. A replay of past weeks can show which gaps it would have chosen and when.

## Build order

The name and what to call them first (the pinned address line already exists; asking for it is the missing
half). Then the map and the gap picker in shadow (logged, no note), then the note on a small budget, then depth
by stage and backing off.
