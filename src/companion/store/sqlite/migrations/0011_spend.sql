-- One row per paid model call that came back with a cost, so what the bot spends can be read, summed
-- and capped. Append-only. A call that was cancelled or failed before it answered has no cost to
-- record, so the total can sit slightly under the provider's own bill.

CREATE TABLE spend (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    purpose         TEXT NOT NULL,
    model           TEXT NOT NULL,
    cost_usd        REAL NOT NULL CHECK (cost_usd >= 0),
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX spend_by_time ON spend (relationship_id, at);

CREATE TRIGGER spend_no_update BEFORE UPDATE ON spend
BEGIN SELECT RAISE(ABORT, 'spend is append-only'); END;

CREATE TRIGGER spend_no_delete BEFORE DELETE ON spend
BEGIN SELECT RAISE(ABORT, 'spend is append-only'); END;
