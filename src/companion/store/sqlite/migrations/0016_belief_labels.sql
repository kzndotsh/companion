-- Which part of their life each memory is about and how personal it is (J48, `features/knowing`).
-- A model labels, code counts. A memory can be labelled again; the newest row wins. Append-only.

CREATE TABLE belief_labels (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    domain          TEXT NOT NULL,
    depth           TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX belief_labels_by_belief ON belief_labels (relationship_id, belief_id, id);

CREATE TRIGGER belief_labels_no_update BEFORE UPDATE ON belief_labels
BEGIN SELECT RAISE(ABORT, 'belief_labels is append-only'); END;
CREATE TRIGGER belief_labels_no_delete BEFORE DELETE ON belief_labels
BEGIN SELECT RAISE(ABORT, 'belief_labels is append-only'); END;
