-- An embedding of each memory's claim, for the relevance look-up (`core/relevance.py`). Unit-length
-- float32 vectors; one row per memory and model, the newest wins. Append-only.

CREATE TABLE belief_embeddings (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    model           TEXT NOT NULL,
    vector          BLOB NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX belief_embeddings_by_model ON belief_embeddings (relationship_id, model, belief_id);

CREATE TRIGGER belief_embeddings_no_update BEFORE UPDATE ON belief_embeddings
BEGIN SELECT RAISE(ABORT, 'belief_embeddings is append-only'); END;
CREATE TRIGGER belief_embeddings_no_delete BEFORE DELETE ON belief_embeddings
BEGIN SELECT RAISE(ABORT, 'belief_embeddings is append-only'); END;
