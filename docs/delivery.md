# Sending and receiving

How a message comes in and a reply goes out over Telegram (`io/telegram.py`).

- A message is answered at most once: Telegram updates are recorded before the turn runs.
- A reply the user never received is marked undelivered and left out of what the model reads.
- Replies are held to feel typed: `COMPANION_PACE` is off, quick, natural (default) or slow. Set
  `off` when timing a run by hand. Commands are never held.
- A long, plain reply is sometimes sent as two or three messages (`COMPANION_SPLIT`, on unless
  `off`). The ledger and the history keep it as one reply, so the model never sees the splitting. Cuts
  fall at sentence boundaries only, and a reply with quoted speech (roleplay) is never split
  (`io/split.py`).
- A plain message that arrives while the previous one is still being answered (written or held)
  replaces that answer, and the dropped reply is marked undelivered, so the new reply sees both
  messages. A split reply cut off after some of its messages went out (superseded, or a send that
  failed) is marked too, and the part that arrived is added beside it, so the model reads only what
  was seen. Commands never supersede. The poll offset moves past a message when it is queued, so a
  restart can lose one that was queued but not answered.
