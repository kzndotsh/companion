# 0005. One continuous conversation per relationship

**Status:** accepted 2026-10-15. The clock line moved in part by ADR 0012 (see Since).

## Decision

The talker's history is the last 40 utterances of the relationship, across sessions and days, not
the current day's session. `session_id` stays on every row as a label, and the daemon uses one
constant session (`SESSION = "main"`), but nothing partitions history by it.

## Why

The first version keyed history by UTC date. At UTC midnight, which was 8 pm for the one user, the
companion lost everything and started cold. A person does not reset at a date boundary. The
conversation also needs to survive a restart, and the ledger already does.

## Replay contract

Live and replay must window history identically, or replays drift once a conversation passes the
limit. Both call `ledger.history_before` with `HISTORY_LIMIT`, defined once in `core/history.py`.
A test runs the live loop past the limit and replays every turn.

## Clock

The clock line is rendered once, stored on the turn record, and reused by replay.

Since 2026-10-19, superseded in part by ADR 0012: the line is no longer part of the user's message.
It is a note in the system block ("Right now it is Weekday HH:MM.", plus "Their last message came
N ago." when the gap is a minute or more, not ten). The turn record keeps it in the `card` column.

## Known limit

A raw window is a stopgap. It teaches the model its own earlier mistakes (long replies, a question
every turn) and drops anything older than 40 messages. The memory card (`core/card.py`) now covers
what falls out of the window, and this ADR still holds alongside it. A reply the user never
received is left out of the window (ADR 0002).

## Reverses if

Relationships span multiple channels or people that must not share history.
