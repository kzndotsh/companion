# How a reply is made

This is the path one message takes from arriving to being answered, and the rules that apply to every
reply whatever feature is involved. What each feature adds along the way is in its own README under
`src/companion/features/`.

## The stages

A turn runs in stages, one module each under `src/companion/turn/`, driven by `handle(convo, ...)` in
`fast.py`:

1. **Hear** (`hear.py`). First it decides whether the message needs a reply at all or only a
   reaction emoji, and reads how serious it is (the listening read, below).
2. **Route** (`route.py`). It chooses which talker answers: the everyday model or the roleplay model.
3. **Look** (`notes.py`). Every feature that looks something up before the reply does so here, side
   by side, under one 9 s deadline. A look-up that is late or fails simply adds nothing that turn.
4. **Assemble** (`assemble.py`). It builds the request: the persona, the history, and a system block
   holding the clock, the memory card and the notes. `Layout` lays the request out from those parts
   with no store in reach; `companion eval` lays out a scripted fixture with it too, and passes each
   reply through `checked` in `talk.py`, so a sample is what the person would receive.
5. **Talk** (`talk.py`). The talker writes the reply, and the reply checks run on it.
6. **Persist** (`persist.py`). Their message, the reply and every decision are stored, and each
   feature's step after the turn runs. Shadow look-ups run beside it (`beside.py`) and never change
   the reply.

The values each stage hands the next live in `turn/values.py`. The conversation the turn runs in is
plain data in `loops/conversation.py`.

## Reading the message

Outside a scene, each message is read by a small judge for how serious it is, from 0 (ordinary) to 3
(acute), and for what the person is doing. Code chooses a listening note from that reading
(`core/turn/listening.py`), so a vent gets heard rather than fixed. `COMPANION_LISTEN=off` turns this
off. Acute messages get no note, and there is no crisis path yet.

The same read also labels a message that is rude to the companion (one note for a cooler reply that
turn) and a request to remember something. A recall request is looked up across every memory by a
small model, and what it finds rides that turn's system block (`core/recall.py`).

Memories marked sensitive are on the card only on turns rated 1 or more. A turn that is ordinary,
real (not a scene) and not a goodbye counts as casual (`loops/current.py`, `is_casual`), and many
features only act on casual turns.

When they come back 3 hours or more after a talk that turned serious (severity 2 within its last 12
hours), the next ordinary message gets one gentle note to ask how they are now (`notes/check-in`),
once per heavy talk.

## Which talker answers

Code chooses the talker (`core/turn/floor.py`, ADR 0017). The roleplay talker answers a pretend scene
in progress. With `COMPANION_ROUTE_INTIMATE=on`, it also answers intimate talk, but only once a
message of theirs has been explicit (`system/explicit-lead`, read on each intimate message until one
is), and it carries on while their messages stay intimate. Flirting alone stays with the everyday
talker however long it runs.

A floor sits above all of this, in code and not in any setting. When the listening judge reads the
turn as age-coded, or could not read it at all, it stays with the everyday talker. A fallback model's
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

The notes are chosen by code from models' labels, never written by a model (ADR 0014). They go in a
fixed order (`ORDER` in `turn/notes.py`), and the order is checked when the bot starts. A few lines
go after the history instead, as a system message, because there they change behaviour and in the
system block they did not (measured twice). These are the owned-it note, the question-run note,
the character's scene reminder and the offer of an emoticon of its own. Whatever is sent after the history is logged with
the turn, so a replay rebuilds it.

When one of its last two replies owned a slip ("my bad", "I got that wrong"), the next turn outside a
scene gets `notes/owned-it` after the history: that was enough, no more apologies or self-blame
(`core/turn/ownup.py`).

When each of its last three replies asked them a question, the next turn outside a scene, not
serious and with no other note asking them something gets `notes/question-run` after the history:
ask nothing this time, but leave them something to answer (`core/turn/questions.py`).

## Checking the reply

A reply is checked before it is sent (`core/recheck.py`). Code catches these:

- an em dash
- an AI disclaimer nobody asked for
- the clock line or a tag copied from the system block
- the stock "X, especially when" or "X, even when" line
- the stage direction "a beat"
- markdown that would show raw, outside scenes

On an ordinary turn, a small judge also catches a joke bolted onto an ordinary message, and a canned
generic reaction that could sit under any message ("that sounds so good", "X is always the best part",
restating their point back as praise), in one call (`system/quip`). In a scene, on a
serious or acute turn, or when the listening judge could not read the turn, only the code checks
run.

When a check fails, the same model is asked once more, or twice if the redraw still has an em dash,
and the last reply goes out whatever it is. The first is kept in the decision detail. Nothing is ever
edited. An empty reply is drawn once more instead of leaving the turn silent.
`COMPANION_RESAMPLE=off` turns the checks off.

## When a model fails

A talker that errors is answered by its fallback model at once. One still silent after 10 s has the
fallback asked as well, and the first answer is sent (`models/fallback.py`). The reply carries the
name of the model that wrote it, and every check runs on it as usual. A talker call times out at
25 s. A judge that fails or runs out of time means what its feature says it means, usually "no note
this turn". It never stops the reply.
