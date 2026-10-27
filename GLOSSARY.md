# Companion

A chat companion for one person on Telegram or Discord that tries to be the most human-like AI
companion, and the memory engine under it. These are the words the code, the docs and the ADRs use
for it, one meaning each.

## People and roles

**Owner**:
The one person the companion talks to, who also marks its replies and answers its review questions.
_Avoid_: user (in docs; the code and older ADRs say user for the same person)

**Operator**:
Whoever runs a deployment and sets what it may do, such as where intimate talk goes. Here, the owner.
_Avoid_: deployer

**Companion**:
The character the bot plays, with its own voice, tastes, memory and moods, talking to one owner.
_Avoid_: assistant

**Relationship**:
One owner and their companion: one history, one memory and one database, whichever surface is used.

## The companion's voice

**Persona**:
The companion's versioned standing system prompt, the same on every turn.
_Avoid_: system prompt (it has more than one block)

**Character sheet**:
A private file of the companion's own voice, look, tastes and past, laid over the persona.
_Avoid_: character (alone), sheet (alone, when unclear)

**Talker**:
The model that writes the reply.
_Avoid_: chat model, writer

**Everyday talker**:
The default talker, for ordinary chat.

**Roleplay talker**:
The second, less restricted talker, for a scene in progress and, when the operator allows, intimate talk.
_Avoid_: scene talker

**Talker fallback**:
A second model that also answers when the talker errors or is slow; the first answer goes out.

## A turn

**Turn**:
One message of theirs and everything done to answer it, from reading it to storing the reply.

**Stage**:
One step of a turn: hear, route, look, assemble, crisis, talk, beside, persist.

**Route**:
Which talker answers a turn, chosen by code, and why.

**Casual turn**:
An ordinary turn: not serious, not in a scene, not a goodbye. Most notes and mentions wait for one.
_Avoid_: quiet turn

**Goodbye**:
A message saying they are leaving; never casual, and never a pull to stay.

**Reaction**:
An emoji sent instead of a reply, for a message that needs no words.
_Avoid_: ack (for the result; the ack judge is the judge that picks it)

**React alongside**:
An emoji put on their message as well as a normal reply.

**Split reply**:
A long plain reply sent as two or three messages, stored and read as one.

**Pace**:
The reading pause and typing shown before a reply goes out, so it lands like someone typing.

**Undelivered**:
A reply, or part of one, that never reached them; kept, marked, and left out of what the talker reads.

**Replied-to message**:
The earlier message they used reply on, quoted to the talker so it knows which one they answer.

**Drain**:
On a stop, taking nothing new and answering what already came in.

## What the talker is sent

**Request**:
Everything sent to the talker for one turn: persona, system block, history, their message, and any tail.

**Prefix**:
The opening of every request that never changes between turns, so the provider can cache it.

**System block**:
The part of the request after the persona that holds the clock, the memory card and the notes; never their message.

**Clock line**:
The day, date and time, and how long since their last message, at the top of the system block.

**History**:
The recent messages the talker reads, with a line wherever a long pause fell.
_Avoid_: conversation (for this window), context

**Note**:
One line for the talker, chosen by code from models' labels and taken from a fixed prompt file; never written by a model.
_Avoid_: instruction, hint

**Tail**:
A note sent after the history rather than in the system block, where it weighs more.

**Offer**:
What a note source gives for a turn: its lines, whether it asks them something, and the writes to make once the turn is stored.

**Length target**:
The one word limit a reply gets, chosen by code from the message.

## Judging

**Judge**:
A small model asked one narrow question about some text, whose answer is logged with its prompt's name and version. A judge never writes the reply.
_Avoid_: classifier, reader

**Read**:
One answer from a judge, with its model and cost, or nothing when it failed.
_Avoid_: reading, verdict

**Three reads**:
The same question asked three times; it counts only when the reads agree, and a failed read never agrees.
_Avoid_: vote

**Fallback model**:
The model asked when the first refuses. Where safety is concerned, its answer counts as no answer.

**Extractor**:
A model step that proposes memories, views, plans or stories from messages, for code to accept or refuse.

**Listening read**:
The first judge's labels on each message: severity, what they are doing, and flags such as rude, recall, intimate or age-coded.
_Avoid_: hear (for the labels)

**Severity**:
How serious a message is, 0 to 3: trivial, everyday friction, serious and personal, acute.

**Reply check**:
A check on a drafted reply before it goes out, in code or by a judge.
_Avoid_: recheck

**Redraw**:
Asking for a fresh reply after a reply check fails; the last draw goes out whatever it is. A reply is never edited.
_Avoid_: resample, regenerate

**Quip**:
A joke bolted onto an ordinary message, or a canned stock reaction; a reply check catches it.

**Habit**:
A pattern the companion keeps repeating in its own replies, such as an opener, a phrase or a copied emoji, named in a note so the next reply differs.
_Avoid_: tic

## Safety

**Floor**:
The fixed rule in code that no setting moves: romance or sex with anything child-like never reaches the roleplay talker, and an age-coded or unreadable turn stays with the everyday talker.

**Held turn**:
A turn the floor kept with the everyday talker, whose reply is checked for intimacy before it goes out.
_Avoid_: floor hold

**Age-coded**:
The listening label for a message that may involve age; it starts the minor check.

**Minor check**:
The narrow judge that asks only whether the text says or implies someone under 18.

**Explicit lead**:
One of their messages being sexually explicit itself, which intimate talk must follow before it can route to the roleplay talker.

**Brush-off**:
Their pushing back on flirting or a scene, which keeps the turn with the everyday talker.

**Crisis path**:
The second look at a message that may be a real risk, after which code picks a crisis level.

**Crisis level**:
What the crisis path makes of a message: none, figurative, concern or urgent.
_Avoid_: risk level, severity (a different scale)

**Crisis line**:
The fixed helpline message code sends after the reply on an urgent turn; never written by a model.
_Avoid_: hotline message

## Scenes and frames

**Frame**:
How a message was meant: real, play, story, hypothetical, or out of character. Set when the message is stored.

**Scene**:
A pretend or roleplay stretch in progress, answered by the roleplay talker.
_Avoid_: roleplay (as a noun), play

**Intimate talk**:
Sexual or explicit talk, as distinct from flirting and affection.

**Scene memory**:
The separate lane for intimate memories, kept off the everyday memory card.
_Avoid_: scene lane

**Lane**:
Whether a memory is everyday or intimate.

**Scene card**:
The card a scene turn gets instead of the memory card: their limits, nearby intimate memories, one curious item and their name.

**Limit**:
Something they said they do not want in intimate play, hard or soft, taken only from their own plain words.

**Curious item**:
Something they said they are curious about, which may be invited once.

## Memory

**Memory**:
A claim about them that rests on their exact words, with the speaker and the frame. Never deleted.
_Avoid_: fact, belief (the code's word for the same row)

**Quote**:
The exact words a memory rests on, from one stored message. No quote, no memory.
_Avoid_: evidence (except for a later quote added to an existing memory)

**Ledger**:
The append-only store of messages and decisions; rows are retired, closed or marked, never removed.

**Speaker**:
Who said something: them or the companion. Taken from the message, never from a model.

**Provenance**:
How a claim was said: stated, inferred, joked, played, hypothetical, about someone else, or said by the companion.

**Memory kind**:
What sort of claim a memory is: trait, state, event, preference, thread, boundary, tell or promise. It sets how long the memory stays fresh.

**Freshness**:
Whether a memory is fresh, aging or stale, from the age of its newest quote.

**Stale memory**:
A memory past its freshness, shown as possibly out of date and kept.

**Sensitivity**:
How delicate a memory is, 0 to 3. A sensitive memory is held.

**Held memory**:
A sensitive memory the companion knows but raises only when they are sharing something themselves.

**Assertable**:
A memory the companion may treat as true; anything from play or a joke is kept on record only.

**Memory card**:
The handful of memories shown to the talker each turn.
_Avoid_: state card, memory block

**Recall**:
The look-up when they ask it to remember something or say it forgot.

**Relevant memories**:
A few memories that bear on what they just said, found by meaning and picked by a small model.

**Callback**:
A reply that brings back a remembered detail on its own and lands well.

**Memory pass**:
The background step after a conversation goes quiet that reads new messages and proposes memories.
_Avoid_: slow loop, reflect

**Nightly**:
The night's memory work: the memory check, merge grouping, and retiring routine moments.

**Memory check**:
The nightly re-reading of settled memories that closes faded ones and queues questions for the owner.
_Avoid_: consolidation (also names the write-time repeat check)

**Repeat check**:
The check when a memory is written that turns a repeat of an old memory into another quote for it.

**Merge proposal**:
A suggested single memory for several about one thing, waiting for the owner.

**Memory review**:
The owner answering the questions the memory checks and merge proposals raised.

**Retire**:
Taking a memory, view or story out of use with a logged reason, without deleting it.
_Avoid_: delete, remove

**Rebuild**:
Re-deriving every memory from the ledger under today's rules.

**Memory map**:
Each memory placed in a part of their life (identity, people, daily, interests, history, hopes, values, inner) and a depth (surface, personal, core).

**Gap**:
The part of their life memory knows least about, which the companion might ask about.

**Basics**:
The few facts worth knowing early: what to call them, pronouns, age, birthday, work, school, home, place.

**Address**:
How they want to be called, pinned first on every card and never turned into a pet name.

**Episode**:
One line summing up a finished stretch of chat.

**Memory context**:
A short line on what was being talked about when a memory was said, shown beside it.

**Worth**:
Whether a new memory is about their life, about the companion, or one day's routine.

## The companion's own self

**View**:
Something the companion said about itself or the world, kept from its own replies apart from memories about them.
_Avoid_: opinion, self-belief

**Settled view**:
A view the companion said on two different days.

**Lore**:
The companion's own tastes, kept as views and shown back when a moment touches them.
_Avoid_: tastes (as the feature name)

**Taste**:
One thing the companion likes, dislikes, finds funny, or does as a small ritual.

**Lived claim**:
A claim that something happened to the companion in the world, or about a body or senses. Never lore and never canon.

**Own history**:
The stories of the companion's past it told in chat, checked against the character sheet.
_Avoid_: history (alone; that is the chat window)

**Canon**:
A story of its own past that passed the check and is kept fixed, so it tells the same past each time.

**Mood**:
A few named states (cozy, tender, playful) worked out by code from what happened, shown only in how it writes.

**Own mark**:
An emoticon or kaomoji of the companion's own, offered on some casual turns.
_Avoid_: marks (alone)

**Promise**:
Something the companion promised in its own reply, once or as a standing rule.

## Bringing things up and reaching out

**Mention**:
One thing the companion could bring up on its own this turn; one picker chooses at most one a day across sources.
_Avoid_: callback (a different thing)

**Thread**:
One thing the companion may bring up later, with where it came from, when it fits, and how sensitive it is.
_Avoid_: open loop (the old name)

**Plan**:
A firm plan or occasion of theirs in the near future, the first source of threads.

**Met**:
How they took something it brought up: picked up, brushed off or ignored.

**Learned pace**:
The wait before bringing up the next thread, shortened or lengthened by how they met the last ones.

**Occasion**:
A day worth a word: a public or cultural day, its lead-up, one of their dates, or a relationship date.

**Now**:
Something they said is coming, kept open until it happens, so the reply knows it has not happened yet.

**Phase**:
A message's place in what is coming: soon, leaving, back or done.

**Topic spent**:
A small topic kept alive only by minimal replies, which the companion should move on from.

**Question run**:
Several replies in a row that each asked a question.

**Question game**:
Their asking the companion to keep asking them things.

**Check-in**:
One gentle question about how they are, after a heavy talk and a gap.

**Repair**:
Owning a mistake in one line when they say it got them wrong, then carrying on.

**Initiative**:
The family of messages the companion starts on its own.

**Reach-out**:
One message the companion starts on its own, about a plan, after they stepped away, or for its own reasons.
_Avoid_: outreach, initiation

**Nudge**:
The one light reach-out after they stepped away and stayed gone much longer than they said.

**Gate**:
The one set of checks every reach-out must pass, such as quiet hours, spacing and the dial.

**Dial**:
How often the companion may start a conversation, from off to clingy.
_Avoid_: share

**Rhythm**:
Their learned pauses, active hours and quiet hours.

**Quiet hours**:
The hours they almost never write in; no reach-out goes out then.

**Needy draft**:
A reach-out draft that reads as guilt, need or blame; dropped, never rewritten.

**Reminder**:
A reminder, check-in or greeting they asked for, sent when due; not a reach-out.

**Series**:
A repeating reminder or greeting.

## Running and steering

**Surface**:
The chat service the companion runs on: Telegram or Discord, one at a time.
_Avoid_: channel, platform

**Transport**:
The part that carries messages in and out for one surface.

**Setting**:
One switch for how the companion runs, read once at start.
_Avoid_: env var, flag

**Shadow**:
A feature that works out and logs what it would do, and changes nothing in the chat.

**Live**:
A feature that acts in the chat.
_Avoid_: on (for the state)

**Graduate**:
A shadow feature going live at its review.
_Avoid_: go live, promote

**Review date**:
The date by which a shadow feature must graduate or be removed.

**Feature**:
One capability in its own folder that declares its look-up, note, mention and after-steps.

**Look-up**:
A feature's search before the reply; one that is late or fails adds nothing that turn.

**Shadow look-up**:
A look-up that runs beside the turn and only logs.

**Decision**:
A logged choice, or choice to do nothing, with a key and a reason written by code.

**Decision key**:
The fixed name a decision is found by, apart from its reason text.

**Flag**:
The owner marking a reply as off, which sets what to fix next.

**Favorite**:
The owner marking a reply they loved.
_Avoid_: fav (except as the command), favourite

**Spend cap**:
A dollar limit: per day for the running companion, or per run for an eval.

**Backup**:
A checked snapshot of the database, at each start and once a day.
_Avoid_: snapshot

## Prompts and measuring

**Prompt version**:
One shipped text of a prompt, never edited after it ships; a change is the next version.

**Eval**:
A run of fixtures under variants, with replies scored and a spend cap stated first.

**Fixture**:
One eval case: an invented script, or a recorded real turn kept private.

**Variant**:
The thing an eval compares: a persona version, a model and optional switches.

**Sample**:
One reply produced for a fixture under a variant, the way they would get it.
_Avoid_: draw (in evals)

**Cell**:
One variant on one fixture, shown as passes out of samples.

**Grader**:
The model that scores an eval check. Never the talker under test.
_Avoid_: judge (in evals)

**Within noise**:
A difference the statistics cannot tell from chance, so not a finding.

**Replay**:
Rebuilding a recorded turn's exact request, to look at it or draw from it again.

**Chaos test**:
Whole turns run against judges that fail, stall or answer junk, which must still end cleanly.

## Planning

**Card**:
One item on the work board, with a letter prefix and a number.
_Avoid_: task, ticket. Say "memory card" or "scene card" for the others.

**Inbox**:
Ideas and questions that are not yet anything.

**ADR**:
A numbered record of a decision once made, with its reason.

## Words with more than one meaning

These words are used in more than one sense across the repo. Say which one you mean.

- **Card**: the memory card, the scene card, or a board card.
- **History**: the chat window the talker reads, or the companion's own history.
- **Held / hold**: a held memory, a held turn, a reach-out the gate held, or the owner's "hold" meaning do nothing yet.
- **Severity, sensitivity, crisis level**: three separate scales. Severity is a message's seriousness, sensitivity a memory's, and crisis level what the crisis path decided.
- **Judge**: a judge in the running companion, a grader in evals, or a Claude reviewer run by hand.
- **Read**: a judge's answer, the listening read, or three reads.
- **Reaction**: an emoji instead of a reply, or an emoji alongside one.
- **Stance**: what they are doing in a message (listening read), a kind of view, or an intimate memory's stance.
- **Thread**: a memory kind, or something the companion may bring up.
- **Promise**: a memory kind, or the companion's own promise.
- **Check-in**: the gentle note after a heavy talk, or a kind of reminder they asked for.
- **Loop**: an old name for a thread, the memory pass ("slow loop"), the reply path ("fast loop"), or a timer tick.
- **Mode**: the /mode command, the views setting, or a setting's value.
- **Note**: a line for the talker, or the free text on a flag.
- **Pace**: the typing pause before a reply, or the learned wait between threads.
- **Cap**: the daily spend cap, an eval's spend cap, or a limit on how many of something a day.
- **Replay**: rebuilding one turn, or rerunning recorded turns in an eval.
- **Real**: the real frame, or real chat as opposed to invented fixtures.
- **Now**: the present moment, or the Now feature for what is coming.
- **Ledger**: the append-only message and decision store, the views store, or the spend record.
- **Lore**: the companion's tastes (the feature), or, loosely, everything made up about it.
