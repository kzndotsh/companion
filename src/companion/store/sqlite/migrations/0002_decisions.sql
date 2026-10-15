-- Every surfacing, withholding, initiative and policy choice, with its reason. Append-only.
-- This table is the instrument: it is what the replay command and the evals read.

CREATE TABLE decisions (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    trace_id        TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN
        ('surface', 'withhold', 'initiate', 'do_nothing', 'policy')),
    belief_id       TEXT REFERENCES beliefs (id),
    reason          TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    detail          TEXT CHECK (detail IS NULL OR json_valid(detail)),
    at              TEXT NOT NULL,
    CHECK ((kind IN ('surface', 'withhold')) = (belief_id IS NOT NULL))
) STRICT;

CREATE INDEX decisions_by_turn ON decisions (relationship_id, turn_id, at);
CREATE INDEX decisions_by_belief ON decisions (belief_id, at) WHERE belief_id IS NOT NULL;

CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decisions
BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;

CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decisions
BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
