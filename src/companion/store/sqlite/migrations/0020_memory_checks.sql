-- What a judge read about a memory, or a pair of memories, for keeping memory tidy (ADR 0019), and
-- the owner's answers to the questions those checks raise. Both append-only.

CREATE TABLE memory_checks (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    other_id        TEXT,
    reads           TEXT NOT NULL,
    verdict         TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX memory_checks_by_belief ON memory_checks (relationship_id, belief_id);

CREATE TABLE memory_answers (
    id       INTEGER PRIMARY KEY,
    check_id INTEGER NOT NULL REFERENCES memory_checks (id),
    answer   TEXT NOT NULL,
    at       TEXT NOT NULL
) STRICT;

CREATE TRIGGER memory_checks_no_update BEFORE UPDATE ON memory_checks
BEGIN SELECT RAISE(ABORT, 'memory_checks is append-only'); END;
CREATE TRIGGER memory_checks_no_delete BEFORE DELETE ON memory_checks
BEGIN SELECT RAISE(ABORT, 'memory_checks is append-only'); END;
CREATE TRIGGER memory_answers_no_update BEFORE UPDATE ON memory_answers
BEGIN SELECT RAISE(ABORT, 'memory_answers is append-only'); END;
CREATE TRIGGER memory_answers_no_delete BEFORE DELETE ON memory_answers
BEGIN SELECT RAISE(ABORT, 'memory_answers is append-only'); END;
