-- How long a promise of its own lasts (review of 2026-11-03): lasting, about how it treats them
-- until they release it, or moment, about one joke or one moment, in force for a week. The reader
-- labels each when it records it and the owner can relabel; the newest row wins, and a promise
-- with no row is lasting. Append-only.

CREATE TABLE promise_scopes (
    id         INTEGER PRIMARY KEY,
    promise_id TEXT NOT NULL REFERENCES promises (id),
    scope      TEXT NOT NULL CHECK (scope IN ('lasting', 'moment')),
    by         TEXT NOT NULL,
    at         TEXT NOT NULL
) STRICT;

CREATE INDEX promise_scopes_by_promise ON promise_scopes (promise_id, id);

CREATE TRIGGER promise_scopes_no_update BEFORE UPDATE ON promise_scopes
BEGIN SELECT RAISE(ABORT, 'promise_scopes is append-only'); END;
CREATE TRIGGER promise_scopes_no_delete BEFORE DELETE ON promise_scopes
BEGIN SELECT RAISE(ABORT, 'promise_scopes is append-only'); END;
