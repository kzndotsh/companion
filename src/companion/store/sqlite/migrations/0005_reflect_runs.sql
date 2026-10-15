-- One row per slow-loop pass. The latest row is the cursor, so the log is also the progress.

CREATE TABLE reflect_runs (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    upto_at         TEXT NOT NULL,
    upto_id         TEXT NOT NULL,
    n_utterances    INTEGER NOT NULL,
    n_candidates    INTEGER NOT NULL,
    n_accepted      INTEGER NOT NULL,
    n_rejected      INTEGER NOT NULL,
    model           TEXT NOT NULL,
    cost_usd        REAL NOT NULL,
    latency_ms      INTEGER NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX reflect_runs_by_relationship ON reflect_runs (relationship_id);

CREATE TRIGGER reflect_runs_no_update BEFORE UPDATE ON reflect_runs
BEGIN SELECT RAISE(ABORT, 'reflect runs are append-only'); END;

CREATE TRIGGER reflect_runs_no_delete BEFORE DELETE ON reflect_runs
BEGIN SELECT RAISE(ABORT, 'reflect runs are append-only'); END;
