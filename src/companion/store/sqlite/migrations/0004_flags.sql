-- The user marks turns as failures. Append-only: a flag is evidence, not a to-do.

CREATE TABLE flags (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    turn_id         TEXT NOT NULL REFERENCES turn_requests (turn_id),
    kind            TEXT NOT NULL CHECK (kind IN ('off', 'forgot', 'too_much', 'unwanted')),
    note            TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX flags_by_turn ON flags (relationship_id, turn_id);

CREATE TRIGGER flags_no_update BEFORE UPDATE ON flags
BEGIN SELECT RAISE(ABORT, 'flags are append-only'); END;

CREATE TRIGGER flags_no_delete BEFORE DELETE ON flags
BEGIN SELECT RAISE(ABORT, 'flags are append-only'); END;
