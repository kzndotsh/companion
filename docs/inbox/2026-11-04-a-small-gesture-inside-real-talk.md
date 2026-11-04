# A small gesture inside real talk

From a feedback thread about another companion service (summary in the local
`docs/research/2026-11-04_animates-feedback-research.md`). Users' most repeated ask: when they write a
small action in an ordinary chat ("*pours you a drink, clinks glasses* so how's your evening?"),
the companion should act back in kind, not answer with talk alone. Theirs did it only in intimate
scenes. Users' rule of thumb: they act, it acts; they never do, it never does.

## How ours would handle it (read from the code, not tested)

- Any `*action*` is a cue, so the frame judge reads the message. If it calls the message play, the
  whole message is stored as pretend: whatever real thing they said beside the gesture ("rough day,
  my boss...") never reaches memory, and the next message of theirs that is play starts a scene,
  which moves the talk to the roleplay talker with the scene notes.
- A lone short action ("*explodes*") already does not start a scene (`core/frames.py`
  `reaction`, 2026-10-24).
- The persona allows one action in asterisks only "inside a scene they started".

So the likely failures are the reverse of theirs: a gesture over real talk turns the chat into a
scene, and the real part is forgotten.

## Our data

45 of 1,762 of their messages mix an action with real words, nearly all inside intimate scenes. No
everyday gesture yet. Nothing to fix until one happens or a fixture shows the failure.

## If it comes up

- A fixture of three or four everyday gestures over real talk (a drink, a hand held while telling about
  their day): does it act back once, stay on the everyday talker, and keep the real part in memory?
  12 samples each.
- A possible frame for it: real talk with a gesture is real, with the gesture noted, not play.
