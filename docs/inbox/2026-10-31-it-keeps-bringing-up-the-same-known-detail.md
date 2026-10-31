# It keeps bringing up the same known detail

Added 2026-10-31.

## What was noticed

A flag on 2026-10-29: they mention a meal, and the reply asks whether it had the toppings they always
have. It had brought that same detail up several times in the two weeks before, and twice that
evening. The flag's note: it should not always bring a detail up when it did so recently.

## What was measured

Turn replayed as recorded on GPT-6 Luna (`evals/CHANGELOG.md`, 2026-10-31):

| Setup | Replies that name the detail |
|---|---|
| as recorded, the memory in the relevance note | 4/12 |
| memory kept, marked as already brought up, and when | 8/24 |
| memory moved from the note to the card's plain list | 13/24 |
| memory left off | 0/12 |
| only its own matching taste left off | 3/12 |

The memory came from the relevance note ("may bear on what they just said"), not the card. The note
already says never to ask something it answers, and the reply asked anyway. Marking or moving the
memory did not help; only leaving it off did.

From the log and the chat:

- The relevance note made 158 offers covering 68 memories in nine days. 90 offers were memories it
  had offered before; one was offered 14 times.
- A read of two weeks of chat found 19 details brought up unasked. 6 came back within a week, each
  time on the same kind of topic (a drink, a meal, a project). A detail was also repeated inside one
  conversation four times.
- They met most of these warmly the first time. Repeats got flatter replies, and asking about something
  it already knew got a "you know this already". The only clear annoyance came when it brought up a
  health detail unasked.

## Outside

- OP-Bench (EMNLP 2026, arXiv 2601.13722) calls this over-personalization: irrelevance, repetition
  and sycophancy. About half its 1,700 cases are repetition. Every memory system it tested overused
  memories. Its fix, a small model that drops memories a query does not need, cut it about 29%. Our
  relevance picker is already that filter, and it still picked this memory. It does not test
  instructions alone.
- "Mitigating Over-Personalization via Structured Memory" (arXiv 2608.08300): grouping memories by
  life area cut leakage a little. Dropping every memory below a similarity cutoff cut leakage sharply
  but raised failures to use a helpful memory from 23% to 71%. A ban has to be narrow.
- MGRetrieval (arXiv 2605.27437) filters out memories already pulled in on earlier turns, close to a
  cooldown.
- Users of other assistants report the same thing: one detail, such as a wake-up time or a diet,
  brought up again and again.

## Options, best first

1. **A cooldown on the relevance note.** A memory the note offered in the last 7 days is not offered
   again. The card is untouched, the history is already in `relevance: what it was shown`, and it
   costs no new model call. Cost: for that week it may ask what it already knows instead ("what did
   you put on it?" came up in about 1 in 4 replies even with the memory shown).
2. **A cooldown only on memories a reply actually used.** The callbacks judge runs after each reply
   and records which memory it brought up. More precise, a little spend a day, more code. Only if 1
   proves too blunt.
3. **Learn the pace from how they met it**, as threads do (ADR 0023): a detail met warmly may come back
   sooner, a flat one waits longer. A later step on top of 1 or 2.
4. **Health memories never in the relevance note**, only when they raise it. Cheap, but it rests on a
   single annoyed reply.

Not worth trying: rewording the note, or a reply check that blocks asking about something it knows.
Prompt rules like this already failed on this turn.

## How to rerun

A scratch script loads the turn with `store/sqlite/replay.py` `replay_file`, edits `request.card`,
and sends it N times with `OpenRouterTalker.reply`. About $0.002 per 24 replies.
