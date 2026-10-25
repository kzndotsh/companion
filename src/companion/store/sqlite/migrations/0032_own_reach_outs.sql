-- Reach-outs for its own reasons (ADR 0021): one row per reach-out it would send (shadow), sends
-- (live), or drafted and dropped (the draft failed the code check). Kind, the one thing, the draft and
-- the numbers behind it (rhythm, share, dial) are kept as they were. Append-only.

CREATE TABLE own_reach_outs (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    kind            TEXT NOT NULL,
    thing           TEXT NOT NULL,
    draft           TEXT NOT NULL,
    mode            TEXT NOT NULL CHECK (mode IN ('shadow', 'live', 'dropped')),
    detail          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX own_reach_outs_by_time ON own_reach_outs (relationship_id, at);

CREATE TRIGGER own_reach_outs_no_update BEFORE UPDATE ON own_reach_outs
BEGIN SELECT RAISE(ABORT, 'own_reach_outs is append-only'); END;
CREATE TRIGGER own_reach_outs_no_delete BEFORE DELETE ON own_reach_outs
BEGIN SELECT RAISE(ABORT, 'own_reach_outs is append-only'); END;
