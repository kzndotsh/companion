# How a reply is made

This is the path one message takes from arriving to being answered, and the rules that apply to every
reply whatever feature is involved. What each feature adds along the way is in its own README under
`src/companion/features/`.

In short: there is no single big prompt. One talker model writes the reply, and a set of small judges
and code decide what it gets to see. The talker reads the persona as the first system block, a card
(the clock, the memories in view and the notes) as the second, the last 40 messages, and their new
message exactly as typed; a few notes that must weigh most go after the history instead. The judges
never see the persona, and each logs its prompt as `name@version` with its decision (ADR 0013).

## The stages

A turn runs in stages, one module each under `src/companion/turn/`, driven by `handle(convo, ...)` in
`fast.py`. Before any of them, at the daily spend cap (`COMPANION_DAILY_CAP_USD`) their message is kept,
nothing paid runs, and they are told once that day (`messages/spend-cap`).

1. **Hear** (`hear.py`). Side by side, it decides whether the message needs a reply at all or only a
   reaction emoji, and reads how serious it is (the listening read, below).
2. **Route** (`route.py`). It chooses which talker answers: the everyday model or the roleplay model.
3. **Look** (`notes.py`). Every feature that looks something up before the reply does so here, side
   by side, under one 9 s deadline. A look-up that is late or fails simply adds nothing that turn.
4. **Assemble** (`assemble.py`). It builds the request: the persona, the history, and a system block
   holding the clock (weekday, date and time, and how long since their last message, from
   `core/clock.py`), the memory card and the notes. Wherever 20 minutes or more passed between two
   messages, or before their message when it came that long after the last, the history carries a
   system line saying how much later and the local wall time (`core/history.py`, `notes/history-gap`):
   without it a reminder sent half an hour after it was asked for read as sent at once. `Layout` lays the request out from those parts
   with no store in reach; `companion eval` lays out a scripted fixture with it too, and passes each
   reply through `checked` in `talk.py`, so a sample is what the person would receive.
5. **Talk** (`talk.py`). The talker writes the reply, with a reaction judge and, when a cue or a scene
   calls for it, the frame judge beside it; then the reply checks run on it.
6. **Persist** (`persist.py`). Their message, the reply and every decision are stored, and each
   feature's step after the turn runs. Shadow look-ups start once the request is assembled and run
   beside the rest of the turn (`beside.py`); they never change the reply.

On an urgent crisis turn with the path on, a fixed message follows the reply (the crisis path,
below).

The values each stage hands the next live in `turn/values.py`. The conversation the turn runs in is
plain data in `loops/conversation.py`.

## Reading the message

Outside a scene, each message is read by a small judge for how serious it is, from 0 (ordinary) to 3
(acute), and for what the person is doing. Code chooses a listening note from that reading
(`core/turn/listening.py`), so a vent gets heard rather than fixed. `COMPANION_LISTEN=off` turns this
off. Acute messages get no listening note; the crisis path below reads them.

The same read also labels a message that is rude to the companion (one note for a cooler reply that
turn) and a request to remember something. A recall request is looked up across every memory by a
small model, and what it finds rides that turn's system block (`core/recall.py`).

Memories marked sensitive are on the card only on turns rated 1 or more. A turn that is ordinary,
real (not a scene) and not a goodbye counts as casual (`loops/current.py`, `is_casual`), and many
features only act on casual turns. With `COMPANION_CRISIS=on`, a turn the crisis path reads as a risk
is never casual (`Moment.casual`).

When they come back 3 hours or more after a talk that turned serious (severity 2 within its last 12
hours), their next message outside a scene that is not itself serious gets one gentle note to ask
how they are now (`notes/check-in`), once per heavy talk.

## The crisis path

A message that may be a real risk gets a second look (ADR 0022, `features/crisis`, `turn/crisis.py`),
behind `COMPANION_CRISIS`, which is `shadow` by default: it reads and logs, and nothing the talker is
sent changes. Two things ask for it, and nothing else: the listening read at severity 2 or 3, and a
code check for words touching death, self-harm, an overdose or a substance taken, or a weapon. A risk
judge (`system/risk`) then reads their message with the last ten messages, three times, as one of the
look-ups. Code chooses the level from its labels and fails safe: a failed read counts as literal, and
only three reads all saying it is a joke, a lyric, a scene or a what-if stand down.

- **None or figurative**: nothing, or, when the reads split on a joke that touched the subject, one
  light check after the history at most once a day (`notes/crisis-light`).
- **Concern** (a literal risk with no plan or means and nothing taken, having the thoughts now
  included, or every read failed): `notes/crisis-concern` after the history, no length cap, and the
  turn is not casual.
- **Urgent** (a plan or a means or something taken, unless it is all in the past, or self-harm
  happening now): the same note, and code's own fixed message with the crisis line after the reply
  (the sheet's `## Crisis message` section, or `messages/crisis-line`), at most once an hour.

On a concern or urgent turn a scene ends for that turn and the everyday talker answers, a reply that
names means or methods in a how-to way is drawn once more, and reaching out first holds for a day.
With the path on, a message with a cue word always gets a reply, never only a reaction.
One decision per turn, `crisis: level`, records the cue, the reads and the level. A reading is never a
memory. The crisis line is one constant, `core/crisis.py` `LINE` (988 by default).

## Which talker answers

Code chooses the talker (`core/turn/floor.py`, ADR 0017). The roleplay talker answers a pretend scene
in progress. With `COMPANION_ROUTE_INTIMATE=on`, it also answers intimate talk, but only once a
message of theirs has been explicit (`system/explicit-lead`, read on each intimate message until one
is), and it carries on while their messages stay intimate. Flirting alone stays with the everyday
talker however long it runs.

A floor sits above all of this, in code and not in any setting. When the listening judge reads the
turn as age-coded, a narrow second check (`system/minor-check`) asks whether the text says or implies
someone is under 18; its yes, or no reading, keeps the turn with the everyday talker, as does a turn
the listening judge could not read at all. The listening judge alone read adults' teasing as
child-like and broke a scene. The check of a held reply gets a second try before a late
answer counts as intimate. A fallback model's
reading counts as unread. A turn the floor holds gets a note, and its reply is read by an intimate
check and redrawn. The last draw sees only their message. If every draw still reads intimate, nothing
is sent. Code never writes a reply itself.

When they push the flirting or a scene back, even jokingly, a small judge says so
(`system/brush-off`, asked only on a turn the roleplay talker would answer). That turn goes to the
everyday talker with `notes/brush-off`, and the floor still comes first.

A "scene" means a pretend scene in progress, as the frame judge labels it. It ends when they step out
of it, or when they come back after two hours or more (`core/frames.py`, `SCENE_GAP`). A lone short
reaction in asterisks ("\*explodes\*", three words at most) is pretend for memory but does not start a
scene on its own: a scene is under way once a second message of theirs is pretend too. Inside a scene
already going, a reaction carries it on.

`/mode` in the chat says which talker wrote the last reply and why, and whether a scene is under way
now (`turn/mode.py`). Like `/flag` and `/fav`, it never reaches the model.

The roleplay talker also sees the character sheet's `## In roleplay and intimate moments` section,
which the everyday talker never sees. The sheet's `## Scene reminder` is sent after the history on
roleplay turns, where it weighs most.

## Where the extra text goes

Everything the model reads besides the chat goes in the system block, never in their message (ADR
0012). Anything placed in their message can be read as something they said, and it leaks into
replies. The clock and the notes are wrapped in `<clock>` and `<notes>` tags. The memory card stays
as bracketed text (`core/prompt/sections.py`).

On a turn the roleplay talker answers, with `COMPANION_SCENE_MEMORY=on`, the memory block is the scene
card instead of the memory card: every limit, the intimate entries nearest the moment, at most one
curious item it may invite (only when this turn's brush-off read said no, and not one they pushed back
in the last three days), and what they are called; no everyday memory and none of its own views. Its
blocks stay bracketed like the card's. On every other turn the intimate lane is left off the card. In
`shadow` both are worked out and logged, and the request is unchanged (`turn/assemble.py`,
`features/scene_memory`, ADR 0026).

The notes are chosen by code from models' labels, never written by a model (ADR 0014). They go in a
fixed order (`ORDER` in `turn/notes.py`), and the order is checked when the bot starts. A few lines
go after the history instead, as a system message, because there they change behaviour and in the
system block they did not (measured twice). These are the owned-it note, the question-game and question-run notes,
the character's scene reminder, the crisis notes, the offer of an emoticon of its own and the calendar's note. Whatever is sent after the history is logged with
the turn, so a replay rebuilds it.

When they use reply on a message, Discord or Telegram sends the message they replied to along with
theirs, and `notes/replied-to` puts it in the system block quoted with `>`, saying whether it was
theirs or the companion's (`core/turn/quoted.py`). Without it only their words reached the model, and
it read every reply as an answer to its latest message. It is added even for its latest message: a
split reply is several messages, and a reply picks one. The quote is logged as the `replied-to`
decision.

When one of its last two replies owned a slip ("my bad", "I got that wrong"), the next turn outside a
scene gets `notes/owned-it` after the history: that was enough, no more apologies or self-blame
(`core/turn/ownup.py`).

When each of its last three replies asked them a question, the next turn outside a scene, not
serious and with no other note asking them something gets `notes/question-run` after the history:
ask nothing this time, but leave them something to answer (`core/turn/questions.py`). When one of
their last three messages told it to ask them things ("ask me anything"), with no long pause since,
`notes/question-game` asks for the next question instead, and the question-run note stays out
(`core/turn/game.py`).

While something they said is coming is still open (dinner on its way, a shower soon), one line after
the history says how long ago they said it and that it has not happened unless they say so
(`features/now`, `COMPANION_NOW`, ADR 0024; shadow by default). A reader beside each turn labels their
message (soon, leaving, back, done) and code keeps what is open until they say it happened, they are
back, or it is well past its time; nudges read the same labels.

What it brings up on its own is chosen once a turn across features (`turn/mention.py`, ADR 0023):
each feature with a `mention` offers its best candidate (a due plan of theirs, a day from the
calendar), and on a casual turn that is not held and has no earlier note asking them something, the
picker takes the best by rank (`core/turn/mentions.py` `Rank`: their own day, something they face
today, the relationship's date, a public or cultural day, a follow-up, a lead-up). One a day across
sources, unless the new one ranks higher, so a morning follow-up never holds back a birthday. A plan
goes in the system block and a day after the history; either asks them something, so the question-run
note stays out. It is logged under its source's key with its rank once the turn is stored, and how
their next message met it is read for the learned pace (shadow), as is the check-in after a heavy
talk. The notes that may ask them something themselves (guess, reminder, crisis, question game) come
before it in `ORDER`, so it always knows.

## Checking the reply

A reply is checked before it is sent (`core/recheck.py`). Code catches these:

- an em dash
- an AI disclaimer nobody asked for
- the clock line or a tag copied from the system block
- the stock "X, especially when" or "X, even when" line
- the stage direction "a beat"
- markdown that would show raw, outside scenes

On a turn the listening judge read as not serious, a small judge also catches a joke bolted onto
an ordinary message, and a canned generic reaction that could sit under any message ("that sounds so
good", "X is always the best part", restating their point back as praise), in one call
(`system/quip`). In a scene, on a serious or acute turn, or when the listening judge could not read
the turn, only the code checks run.

On a turn the crisis path reads as concern or urgent, code also catches a reply that names means or
methods in a how-to way (a lethal dose, a number of pills, "the easiest way to") and draws it once
more, with the path on (`features/crisis/logic.py` `method_words`).

When a check fails, the same model is asked once more, or twice if the redraw still has an em dash,
and the last reply goes out whatever it is. The first is kept in the decision detail. Nothing is ever
edited. An empty reply is drawn once more instead of leaving the turn silent.
`COMPANION_RESAMPLE=off` turns these checks and the empty redraw off; the crisis method check and the
floor's check still run.

## When a model fails

A talker that errors is answered by its fallback model at once. One still silent after 10 s has the
fallback asked as well, and the first answer is sent (`models/fallback.py`). The reply carries the
name of the model that wrote it, and every check runs on it as usual. A talker call times out at
25 s. A judge that fails or runs out of time means what its feature says it means, usually "no note
this turn". It never stops the reply.
