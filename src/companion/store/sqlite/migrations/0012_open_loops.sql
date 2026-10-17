-- Things they said about their near future that a friend would ask about later. A loop is written
-- once with the exact words it came from; what happens to it afterwards is a row in
-- open_loop_events, and the newest event is its state. A reach-out is a message about a loop, sent
-- or, in shadow mode, only drafted. All three tables are append-only.

CREATE TABLE open_loops (
    id                  TEXT PRIMARY KEY,
    relationship_id     TEXT NOT NULL,
    claim               TEXT NOT NULL,
    quote               TEXT NOT NULL,
    source_utterance_id TEXT NOT NULL REFERENCES utterances (id),
    follow_up_at        TEXT NOT NULL,
    sensitivity         INTEGER NOT NULL CHECK (sensitivity BETWEEN 0 AND 3),
    created_at          TEXT NOT NULL
) STRICT;

CREATE TABLE open_loop_events (
    id      INTEGER PRIMARY KEY,
    loop_id TEXT NOT NULL REFERENCES open_loops (id),
    state   TEXT NOT NULL CHECK (state IN ('open', 'asked', 'resolved', 'expired', 'dropped')),
    reason  TEXT NOT NULL,
    at      TEXT NOT NULL
) STRICT;

CREATE INDEX open_loop_events_by_loop ON open_loop_events (loop_id, id);

CREATE TABLE reach_outs (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    loop_id         TEXT NOT NULL REFERENCES open_loops (id),
    mode            TEXT NOT NULL CHECK (mode IN ('shadow', 'live')),
    draft           TEXT NOT NULL,
    reason          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX reach_outs_by_time ON reach_outs (relationship_id, at);

CREATE TRIGGER open_loops_no_update BEFORE UPDATE ON open_loops
BEGIN SELECT RAISE(ABORT, 'open_loops is append-only'); END;
CREATE TRIGGER open_loops_no_delete BEFORE DELETE ON open_loops
BEGIN SELECT RAISE(ABORT, 'open_loops is append-only'); END;
CREATE TRIGGER open_loop_events_no_update BEFORE UPDATE ON open_loop_events
BEGIN SELECT RAISE(ABORT, 'open_loop_events is append-only'); END;
CREATE TRIGGER open_loop_events_no_delete BEFORE DELETE ON open_loop_events
BEGIN SELECT RAISE(ABORT, 'open_loop_events is append-only'); END;
CREATE TRIGGER reach_outs_no_update BEFORE UPDATE ON reach_outs
BEGIN SELECT RAISE(ABORT, 'reach_outs is append-only'); END;
CREATE TRIGGER reach_outs_no_delete BEFORE DELETE ON reach_outs
BEGIN SELECT RAISE(ABORT, 'reach_outs is append-only'); END;
