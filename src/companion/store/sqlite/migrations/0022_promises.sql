-- The promises the companion made in its own replies (J12), each with the quote from the message it
-- was said in. A mark records what became of one (the owner called it not a promise, or retired it);
-- a promise with no mark is current. Append-only.

CREATE TABLE promises (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    utterance_id    TEXT NOT NULL REFERENCES utterances (id),
    quote           TEXT NOT NULL,
    claim           TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('standing', 'once')),
    avoid           TEXT NOT NULL,
    at              TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    recorded_at     TEXT NOT NULL
) STRICT;

CREATE INDEX promises_by_rel ON promises (relationship_id, at);

CREATE TABLE promise_marks (
    id         INTEGER PRIMARY KEY,
    promise_id TEXT NOT NULL REFERENCES promises (id),
    mark       TEXT NOT NULL CHECK (mark IN ('not_a_promise', 'retired')),
    reason     TEXT NOT NULL,
    at         TEXT NOT NULL
) STRICT;

CREATE TRIGGER promises_no_update BEFORE UPDATE ON promises
BEGIN SELECT RAISE(ABORT, 'promises is append-only'); END;
CREATE TRIGGER promises_no_delete BEFORE DELETE ON promises
BEGIN SELECT RAISE(ABORT, 'promises is append-only'); END;
CREATE TRIGGER promise_marks_no_update BEFORE UPDATE ON promise_marks
BEGIN SELECT RAISE(ABORT, 'promise_marks is append-only'); END;
CREATE TRIGGER promise_marks_no_delete BEFORE DELETE ON promise_marks
BEGIN SELECT RAISE(ABORT, 'promise_marks is append-only'); END;
