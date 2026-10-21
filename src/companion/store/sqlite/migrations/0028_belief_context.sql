-- What they were talking about when a memory was said (J51), written once per memory from the
-- conversation around its quote. Append-only; the newest row for a memory is its context.

CREATE TABLE belief_context (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    context         TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX belief_context_by_belief ON belief_context (relationship_id, belief_id, id);

CREATE TRIGGER belief_context_no_update BEFORE UPDATE ON belief_context
BEGIN SELECT RAISE(ABORT, 'belief_context is append-only'); END;
CREATE TRIGGER belief_context_no_delete BEFORE DELETE ON belief_context
BEGIN SELECT RAISE(ABORT, 'belief_context is append-only'); END;
