# Keep the companion's own refusals from becoming views it holds

Added 2026-10-15. Nothing is decided. This is parked until there is time to try it.

## What happened

The memory step reads the companion's own replies as well as the user's, and records things it
expressed as views it holds (tastes, opinions, promises). During a long flirty roleplay the
companion declined to go further several times, in the moment, in reply to the user pushing. The
memory step then saved five of those as "promises", for example "will not go into explicit
sexual play" and "chooses to keep the flirting sweet rather than explicit".

None of them reached the model's memory, because views need the user's approval first. But if one
had been approved, a limit stated once in the heat of a scene would have become part of who the
companion is, and it would have been told to hold to it. That would entrench the exact behaviour
(stalling and cooling a scene down) that the user wanted less of. Separately, the same step also
wrote a judgemental note about the user ("repeatedly tried to push… testing its limits"), which
was closed by hand.

## The idea

Do not store a view when the companion is declining something the user asked for. Keep its
tastes, jokes, opinions, and commitments the user asked for.

A prompt line saying "skip refusals" asks the model to judge something fuzzy, and prompt-only
rules have failed repeatedly here. A more reliable way is to split the job in two:

1. The model answers easier, factual questions about each candidate view:
   - Why was it said: volunteered, or in response to a request or push from the user?
   - Which direction: does it commit to doing something, or decline to do something?
   - What is it about: its own taste or opinion, or its conduct toward the user?
2. Code applies the policy and writes the logged reason. A decline made in response to a request,
   about its conduct toward the user, is not stored. The model's labels and scores are logged,
   as with the existing ack, frame and reaction judges. The model never writes the reason.

| Said | Why | Direction | Stored |
|---|---|---|---|
| "I think pineapple on pizza is fine" | volunteered | taste | yes |
| "I'll check on you tomorrow" | the user asked | commit | yes |
| "I'm not going to take it further" | answering a push | decline | no |
| "I like slow teasing more than rushing" | volunteered | taste | yes |
| "I don't lie to people" | volunteered | general value | yes, could be reviewed |

## Where it will still be wrong

A taste stated while being pushed ("I'd rather keep it slow") is ambiguous. A general value and
a situational refusal can sound alike. Measure agreement on about twenty labelled examples, as
was done for the ack and reaction judges, before relying on it. The approval step remains the
backstop.

Avoid a list of refusal words ("won't", "not going to"). It misfires on harmless sentences and
misses rephrasings.

## Companion rule for the user's side

A related, separate rule: do not record romantic or sexual behaviour inside a play scene as a
belief about the user. Things the user states about themselves, outside the scene, are still
recorded.

## What the change would touch

Only the extraction step for the companion's own views (its schema, its prompt, and a small code
gate), plus fixtures for both rules. Nothing about how the companion speaks.

## Related

- The design question of whether the companion should have a pace of its own for intimacy, with a
  relationship state and a user-chosen dial. That would set the stance directly, which may matter
  more than any memory rule.
- The existing view gates and approval flow, which are the reason none of these reached the model.
