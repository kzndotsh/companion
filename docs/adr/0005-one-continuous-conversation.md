# 0005. One continuous conversation per relationship

**Status:** accepted 2026-10-15.

**Decision.** The talker's history is the last 40 utterances of the relationship, across sessions and days, not the current day's session. `session_id` stays on every row as a label, and the daemon uses one constant session, but nothing partitions history by it.

**Why.** The first version keyed history by UTC date. At UTC midnight, which was 8 pm for the one user, the companion lost everything and started cold. A person does not reset at a date boundary. The conversation also needs to survive a restart, and the ledger already does.

**Replay contract.** Live and replay must window history identically or replays drift once a conversation passes the limit. Both call `ledger.history_before(rel, user.at, HISTORY_LIMIT)` with the limit defined once in `core/history.py`. A test runs the live loop past the limit and replays every turn.

**Clock.** Each user message carries a `[Weekday HH:MM, last message N ago]` line, with the gap shown only when it is 10 minutes or more. It is rendered once, stored on the turn record, and reused by replay.

**Known limit.** A raw window is a stopgap. It teaches the model its own earlier mistakes (long replies, a question every turn) and drops anything older than 40 messages. The state card (plates) and beliefs replace it. This ADR holds until they land.

**Reverses if.** Relationships span multiple channels or people that must not share history.
