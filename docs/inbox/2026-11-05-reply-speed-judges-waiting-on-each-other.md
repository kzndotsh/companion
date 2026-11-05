# Reply speed: the judges wait on each other

Not a task yet. Prompted on 2026-11-05 by a question: when the chat is quick and hyped, should replies
come faster?

## What the pacing does today

Nothing about the moment. The wait (`io/pace.py`) depends only on the length of their message and of the
reply, the `COMPANION_PACE` setting, a random factor of 0.8 to 1.25, and how long the model took.
Nothing reads the mood, the listening labels or how fast they are texting.

In quick exchanges the pacing already adds almost nothing. From the log (about 290 turns, 2026-10-29
to 11-04, matched by each message's `in:` and `answered` lines):

| They replied within | Turns | Answer, median | Its own work | Held by pacing |
|---|---|---|---|---|
| under 10 s | 20 | 5.9 s | 5.3 s | 0.0 s |
| 10 to 30 s | 151 | 7.6 s | 5.8 s | 0.0 s |
| 30 to 60 s | 60 | 8.1 s | 5.8 s | 0.8 s |
| 1 to 5 min | 34 | 8.4 s | 5.7 s | 1.2 s |

Its own work takes longer than the pacing would wait for a short message. So a pace that follows the
moment would change nothing. To be faster in a quick exchange, the turn itself has to do less waiting.
It answered slower than they did in 7 of 171 exchanges under 30 s.

## Where a turn's time goes

Median of about 250 turns, from the `turn ... +Nms` marks and the `companion.judges` timings:

| Step | Median | Waits on |
|---|---|---|
| Listening judge (the ack judge runs beside it) | 1.4 s | nothing |
| Route judges (brush-off, explicit-lead, minor check) | 0 s at the median; 0.9 to 1.9 s on the 99 of 243 turns that need them | listening |
| Look-ups (focus, relevance, recent, ...) and assembling the request | 0.95 s (p90 1.9 s) | listening |
| Talker | 1.3 s | all of the above |
| Quip check (the reaction and frame judges, started with the talker, finish with it), then storing | 0.85 s | the talker |

The talker is about a quarter of the work. The habits and promise checks run after the reply has gone
out, so they cost nothing.

## Ideas

1. **Start the look-ups that do not need the listening read beside it.** Focus, recent and reminders
   ignore it. Relevance reads it for one yes or no (`sharing`), which it could take at the end. A
   look-up could take the listening read as something it waits on only if it needs it. About 0.9 s off
   most turns, and no decision changes.
2. **Run the route judges beside the look-ups, not before them.** About 0.9 to 1.9 s off the turns that
   go through them. The floor still decides the talker before anything is sent, so this changes speed,
   not the rules. It touches the floor, so `tests/turn/test_chaos.py` and the route tests have to keep
   passing.
3. **Keep the quip check.** It caught something in 71 of 326 replies (63 canned generic reactions, 8
   bolted-on jokes). That is worth 0.9 s.
4. **A faster listening judge model.** The biggest single step, but a model switch needs measuring first.

With 1 and 2, an everyday turn would take about 4.8 s of work instead of 5.7 s.

## Caveats

- How fast they replied stands in for "a hyped moment". It is not a label.
- The stored time of a reply is their message's time plus the talker's time, not when it was sent. The
  send time is only in the log (`answered N s after it arrived`).
- The older log files have no `in:` line, so the table covers about a week.
