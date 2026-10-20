-- The made-up facts rate (G42): each judged reply's statements about the user and what supports each.
-- One row per turn, append-only.

CREATE TABLE invented_checks (
    turn_id         TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    statements      TEXT NOT NULL,
    judge           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE TRIGGER invented_checks_no_update BEFORE UPDATE ON invented_checks
BEGIN SELECT RAISE(ABORT, 'invented_checks is append-only'); END;
CREATE TRIGGER invented_checks_no_delete BEFORE DELETE ON invented_checks
BEGIN SELECT RAISE(ABORT, 'invented_checks is append-only'); END;
