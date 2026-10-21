-- Reminders and check-ins they asked for (one-off). The local wall time and its zone are kept with the
-- UTC time, so a reminder means the clock time they said. A reminder's state is its newest event:
-- pending, claimed (being sent), sent, late (sent past its time), expired, cancelled. Append-only.

CREATE TABLE reminders (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('reminder', 'check_in')),
    thing           TEXT NOT NULL,
    quote           TEXT NOT NULL,
    due_at          TEXT NOT NULL,
    local_wall      TEXT NOT NULL,
    zone            TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    created_at      TEXT NOT NULL
) STRICT;

CREATE TABLE reminder_events (
    id          INTEGER PRIMARY KEY,
    reminder_id TEXT NOT NULL REFERENCES reminders (id),
    state       TEXT NOT NULL CHECK (state IN ('pending', 'claimed', 'sent', 'late', 'expired', 'cancelled')),
    reason      TEXT NOT NULL,
    at          TEXT NOT NULL
) STRICT;

CREATE INDEX reminder_events_by_reminder ON reminder_events (reminder_id, id);

CREATE TRIGGER reminders_no_update BEFORE UPDATE ON reminders
BEGIN SELECT RAISE(ABORT, 'reminders is append-only'); END;
CREATE TRIGGER reminders_no_delete BEFORE DELETE ON reminders
BEGIN SELECT RAISE(ABORT, 'reminders is append-only'); END;
CREATE TRIGGER reminder_events_no_update BEFORE UPDATE ON reminder_events
BEGIN SELECT RAISE(ABORT, 'reminder_events is append-only'); END;
CREATE TRIGGER reminder_events_no_delete BEFORE DELETE ON reminder_events
BEGIN SELECT RAISE(ABORT, 'reminder_events is append-only'); END;
