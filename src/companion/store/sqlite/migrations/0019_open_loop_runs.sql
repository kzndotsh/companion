-- The open-loop pass keeps its own bookmark (J25). It used to read each batch once, after the memory
-- pass had already moved the bookmark, so a failed call lost that batch's plans for good. Now each
-- try is a row: ok = 1 moves the bookmark, ok = 0 is a failed try that is read again next pass.
-- It starts where the memory pass's bookmark is, so history is not read again. Append-only.

CREATE TABLE open_loop_runs (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    upto_at         TEXT NOT NULL,
    upto_id         TEXT NOT NULL,
    ok              INTEGER NOT NULL CHECK (ok IN (0, 1)),
    reason          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX open_loop_runs_by_rel ON open_loop_runs (relationship_id, id);

INSERT INTO open_loop_runs (relationship_id, upto_at, upto_id, ok, reason, at)
SELECT r.relationship_id, r.upto_at, r.upto_id, 1, 'started from the memory pass''s bookmark', r.at
FROM reflect_runs r
WHERE r.rowid = (SELECT MAX(r2.rowid) FROM reflect_runs r2 WHERE r2.relationship_id = r.relationship_id);

CREATE TRIGGER open_loop_runs_no_update BEFORE UPDATE ON open_loop_runs
BEGIN SELECT RAISE(ABORT, 'open_loop_runs is append-only'); END;
CREATE TRIGGER open_loop_runs_no_delete BEFORE DELETE ON open_loop_runs
BEGIN SELECT RAISE(ABORT, 'open_loop_runs is append-only'); END;
