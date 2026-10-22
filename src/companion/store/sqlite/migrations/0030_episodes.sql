-- The times they spent together (J12): one row per stretch of chat, with the facts code worked out and
-- one line a small model wrote about it. Points at its first and last message. Append-only.

CREATE TABLE episodes (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    first_id        TEXT NOT NULL,
    last_id         TEXT NOT NULL,
    start_at        TEXT NOT NULL,
    end_at          TEXT NOT NULL,
    messages        INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('everyday', 'scene', 'heavy')),
    scene_share     REAL NOT NULL,
    top_severity    INTEGER NOT NULL,
    firsts          TEXT NOT NULL,
    gist            TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE UNIQUE INDEX episodes_by_span ON episodes (relationship_id, first_id);

CREATE TRIGGER episodes_no_update BEFORE UPDATE ON episodes
BEGIN SELECT RAISE(ABORT, 'episodes is append-only'); END;
CREATE TRIGGER episodes_no_delete BEFORE DELETE ON episodes
BEGIN SELECT RAISE(ABORT, 'episodes is append-only'); END;
