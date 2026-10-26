-- Repeating reminders, check-ins and greetings ("tell me good morning every day"). A series is the
-- standing request: every day or every week on one day, at the wall time they said, or with no time
-- (hour and minute null) at a time learned from when they usually start or end their day (`part`).
-- Its state is its newest event: active, paused (a greeting nobody answered three times running),
-- stopped. Each time it falls is an ordinary row in `reminders` with the series and its number in
-- the series, so claiming, sending and late or expired work as for a one-off. Append-only.
--
-- `reminders` and `reminder_events` are rebuilt to allow the kind `greeting` and the state
-- `skipped` (a greeting not sent because they had already written). Rows are copied as they are.

CREATE TABLE series (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('reminder', 'check_in', 'greeting')),
    thing           TEXT NOT NULL,
    quote           TEXT NOT NULL,
    rule            TEXT NOT NULL CHECK (rule IN ('daily', 'weekly')),
    weekday         INTEGER CHECK (weekday BETWEEN 0 AND 6),
    hour            INTEGER CHECK (hour BETWEEN 0 AND 23),
    minute          INTEGER CHECK (minute BETWEEN 0 AND 59),
    part            TEXT NOT NULL CHECK (part IN ('morning', 'night', 'other')),
    zone            TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    CHECK ((rule = 'weekly') = (weekday IS NOT NULL)),
    CHECK ((hour IS NULL) = (minute IS NULL)),
    CHECK (hour IS NOT NULL OR (kind = 'greeting' AND part IN ('morning', 'night')))
) STRICT;

CREATE TABLE series_events (
    id        INTEGER PRIMARY KEY,
    series_id TEXT NOT NULL REFERENCES series (id),
    state     TEXT NOT NULL CHECK (state IN ('active', 'paused', 'stopped')),
    reason    TEXT NOT NULL,
    at        TEXT NOT NULL
) STRICT;

CREATE INDEX series_events_by_series ON series_events (series_id, id);

CREATE TABLE reminders_next (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('reminder', 'check_in', 'greeting')),
    thing           TEXT NOT NULL,
    quote           TEXT NOT NULL,
    due_at          TEXT NOT NULL,
    local_wall      TEXT NOT NULL,
    zone            TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    series_id       TEXT REFERENCES series (id),
    seq             INTEGER,
    CHECK ((series_id IS NULL) = (seq IS NULL))
) STRICT;

CREATE TABLE reminder_events_next (
    id          INTEGER PRIMARY KEY,
    reminder_id TEXT NOT NULL REFERENCES reminders_next (id),
    state       TEXT NOT NULL CHECK (state IN ('pending', 'claimed', 'sent', 'late', 'expired', 'cancelled', 'skipped')),
    reason      TEXT NOT NULL,
    at          TEXT NOT NULL
) STRICT;

INSERT INTO reminders_next (id, relationship_id, kind, thing, quote, due_at, local_wall, zone,
    turn_id, created_at)
SELECT id, relationship_id, kind, thing, quote, due_at, local_wall, zone, turn_id, created_at
FROM reminders;
INSERT INTO reminder_events_next (id, reminder_id, state, reason, at)
SELECT id, reminder_id, state, reason, at FROM reminder_events;

-- Dropping a table drops its triggers and fires none; the events go first, so nothing refers to
-- the old reminders when it goes. Renaming carries the events' reference over to the new name.
DROP TABLE reminder_events;
DROP TABLE reminders;
ALTER TABLE reminders_next RENAME TO reminders;
ALTER TABLE reminder_events_next RENAME TO reminder_events;

CREATE INDEX reminder_events_by_reminder ON reminder_events (reminder_id, id);
-- Occurrence n + 1 of a series is made only once occurrence n has ended, so one row per number is
-- at most one pending at a time; a second scheduler making the same number is ignored.
CREATE UNIQUE INDEX reminders_one_per_turn_of_series ON reminders (series_id, seq)
WHERE series_id IS NOT NULL;

CREATE TRIGGER reminders_no_update BEFORE UPDATE ON reminders
BEGIN SELECT RAISE(ABORT, 'reminders is append-only'); END;
CREATE TRIGGER reminders_no_delete BEFORE DELETE ON reminders
BEGIN SELECT RAISE(ABORT, 'reminders is append-only'); END;
CREATE TRIGGER reminder_events_no_update BEFORE UPDATE ON reminder_events
BEGIN SELECT RAISE(ABORT, 'reminder_events is append-only'); END;
CREATE TRIGGER reminder_events_no_delete BEFORE DELETE ON reminder_events
BEGIN SELECT RAISE(ABORT, 'reminder_events is append-only'); END;
CREATE TRIGGER series_no_update BEFORE UPDATE ON series
BEGIN SELECT RAISE(ABORT, 'series is append-only'); END;
CREATE TRIGGER series_no_delete BEFORE DELETE ON series
BEGIN SELECT RAISE(ABORT, 'series is append-only'); END;
CREATE TRIGGER series_events_no_update BEFORE UPDATE ON series_events
BEGIN SELECT RAISE(ABORT, 'series_events is append-only'); END;
CREATE TRIGGER series_events_no_delete BEFORE DELETE ON series_events
BEGIN SELECT RAISE(ABORT, 'series_events is append-only'); END;
