-- A judge's reading of one reply: did it bring up a memory on its own, and did that land. Each turn is
-- judged once and the verdict is kept, so a weekly report only pays for new turns. Append-only.

CREATE TABLE callback_checks (
    turn_id         TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    judged_at       TEXT NOT NULL,
    judge           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    callback        INTEGER NOT NULL CHECK (callback IN (0, 1)),
    memories        TEXT NOT NULL,
    accurate        INTEGER NOT NULL CHECK (accurate IN (0, 1)),
    fitting         INTEGER NOT NULL CHECK (fitting IN (0, 1)),
    forced          INTEGER NOT NULL CHECK (forced IN (0, 1))
) STRICT;

CREATE INDEX callback_checks_by_time ON callback_checks (relationship_id, judged_at);

CREATE TRIGGER callback_checks_no_update BEFORE UPDATE ON callback_checks
BEGIN SELECT RAISE(ABORT, 'callback_checks is append-only'); END;
CREATE TRIGGER callback_checks_no_delete BEFORE DELETE ON callback_checks
BEGIN SELECT RAISE(ABORT, 'callback_checks is append-only'); END;
