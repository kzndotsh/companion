-- What moved the mood (ADR 0016). One row per effect; the mood at any moment is worked out from these
-- by `features/mood/logic.py`, never stored. Each row keeps its own state and half-life, so a replay reads it the
-- way it was meant even after the parameters change. Append-only.

CREATE TABLE mood_effects (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    at              TEXT NOT NULL,
    state           TEXT NOT NULL,
    source          TEXT NOT NULL,
    amount          REAL NOT NULL CHECK (amount >= 0),
    half_life_hours REAL NOT NULL CHECK (half_life_hours > 0),
    params          TEXT NOT NULL
) STRICT;

CREATE INDEX mood_effects_by_time ON mood_effects (relationship_id, at);

CREATE TRIGGER mood_effects_no_update BEFORE UPDATE ON mood_effects
BEGIN SELECT RAISE(ABORT, 'mood_effects is append-only'); END;
CREATE TRIGGER mood_effects_no_delete BEFORE DELETE ON mood_effects
BEGIN SELECT RAISE(ABORT, 'mood_effects is append-only'); END;
