-- The user marks turns they loved. Append-only: a favorite is evidence of what to keep.

CREATE TABLE favorites (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    turn_id         TEXT NOT NULL REFERENCES turn_requests (turn_id),
    note            TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX favorites_by_turn ON favorites (relationship_id, turn_id);

CREATE TRIGGER favorites_no_update BEFORE UPDATE ON favorites
BEGIN SELECT RAISE(ABORT, 'favorites are append-only'); END;

CREATE TRIGGER favorites_no_delete BEFORE DELETE ON favorites
BEGIN SELECT RAISE(ABORT, 'favorites are append-only'); END;
