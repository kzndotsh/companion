-- The intimate scene lane (ADR 0026). A lane row places one memory about them: everyday, intimate
-- with its stance, or excluded with the reason; the newest row is its place. A pattern is how they
-- tend to play, noted from scenes, with a quote from each scene it was seen in; an event retires
-- one. The bookmark says how far the scenes have been read. Append-only.

CREATE TABLE scene_lanes (
    id         INTEGER PRIMARY KEY,
    belief_id  TEXT NOT NULL REFERENCES beliefs (id),
    lane       TEXT NOT NULL CHECK (lane IN ('everyday', 'intimate', 'excluded')),
    stance     TEXT CHECK (stance IN
        ('into', 'curious', 'soft_limit', 'hard_limit', 'style', 'aftercare')),
    why        TEXT CHECK (why IN ('doubt', 'floor', 'crisis', 'listening', 'not_their_words')),
    model      TEXT NOT NULL,
    prompt     TEXT NOT NULL,
    at         TEXT NOT NULL,
    CHECK ((lane = 'intimate') = (stance IS NOT NULL)),
    CHECK ((lane = 'excluded') = (why IS NOT NULL))
) STRICT;

CREATE INDEX scene_lanes_by_belief ON scene_lanes (belief_id, id);

CREATE TABLE scene_patterns (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    claim           TEXT NOT NULL CHECK (length(trim(claim)) > 0),
    stance          TEXT NOT NULL CHECK (stance IN ('into', 'curious', 'style')),
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    recorded_at     TEXT NOT NULL
) STRICT;

CREATE TABLE scene_pattern_quotes (
    id           INTEGER PRIMARY KEY,
    pattern_id   TEXT NOT NULL REFERENCES scene_patterns (id),
    scene_key    TEXT NOT NULL REFERENCES utterances (id),
    utterance_id TEXT NOT NULL REFERENCES utterances (id),
    quote        TEXT NOT NULL CHECK (length(trim(quote)) > 0),
    at           TEXT NOT NULL
) STRICT;

CREATE INDEX scene_pattern_quotes_by_pattern ON scene_pattern_quotes (pattern_id, id);

CREATE TRIGGER scene_pattern_quote_is_verbatim BEFORE INSERT ON scene_pattern_quotes
WHEN instr((SELECT text FROM utterances WHERE id = NEW.utterance_id), NEW.quote) = 0
BEGIN SELECT RAISE(ABORT, 'quote does not occur in the source utterance'); END;

CREATE TRIGGER scene_pattern_quote_is_theirs BEFORE INSERT ON scene_pattern_quotes
WHEN (SELECT speaker FROM utterances WHERE id = NEW.utterance_id) != 'user'
BEGIN SELECT RAISE(ABORT, 'a pattern is quoted from their own messages'); END;

CREATE TABLE scene_pattern_events (
    id         INTEGER PRIMARY KEY,
    pattern_id TEXT NOT NULL REFERENCES scene_patterns (id),
    state      TEXT NOT NULL CHECK (state IN ('retired')),
    reason     TEXT NOT NULL,
    at         TEXT NOT NULL
) STRICT;

CREATE TABLE scene_vectors (
    id         INTEGER PRIMARY KEY,
    pattern_id TEXT NOT NULL REFERENCES scene_patterns (id),
    model      TEXT NOT NULL,
    vector     BLOB NOT NULL,
    at         TEXT NOT NULL
) STRICT;

CREATE TABLE scene_reads (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    upto_at         TEXT NOT NULL,
    upto_id         TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE TRIGGER scene_lanes_no_update BEFORE UPDATE ON scene_lanes
BEGIN SELECT RAISE(ABORT, 'scene_lanes is append-only'); END;
CREATE TRIGGER scene_lanes_no_delete BEFORE DELETE ON scene_lanes
BEGIN SELECT RAISE(ABORT, 'scene_lanes is append-only'); END;
CREATE TRIGGER scene_patterns_no_update BEFORE UPDATE ON scene_patterns
BEGIN SELECT RAISE(ABORT, 'scene_patterns is append-only'); END;
CREATE TRIGGER scene_patterns_no_delete BEFORE DELETE ON scene_patterns
BEGIN SELECT RAISE(ABORT, 'scene_patterns is append-only'); END;
CREATE TRIGGER scene_pattern_quotes_no_update BEFORE UPDATE ON scene_pattern_quotes
BEGIN SELECT RAISE(ABORT, 'scene_pattern_quotes is append-only'); END;
CREATE TRIGGER scene_pattern_quotes_no_delete BEFORE DELETE ON scene_pattern_quotes
BEGIN SELECT RAISE(ABORT, 'scene_pattern_quotes is append-only'); END;
CREATE TRIGGER scene_pattern_events_no_update BEFORE UPDATE ON scene_pattern_events
BEGIN SELECT RAISE(ABORT, 'scene_pattern_events is append-only'); END;
CREATE TRIGGER scene_pattern_events_no_delete BEFORE DELETE ON scene_pattern_events
BEGIN SELECT RAISE(ABORT, 'scene_pattern_events is append-only'); END;
CREATE TRIGGER scene_vectors_no_update BEFORE UPDATE ON scene_vectors
BEGIN SELECT RAISE(ABORT, 'scene_vectors is append-only'); END;
CREATE TRIGGER scene_vectors_no_delete BEFORE DELETE ON scene_vectors
BEGIN SELECT RAISE(ABORT, 'scene_vectors is append-only'); END;
CREATE TRIGGER scene_reads_no_update BEFORE UPDATE ON scene_reads
BEGIN SELECT RAISE(ABORT, 'scene_reads is append-only'); END;
CREATE TRIGGER scene_reads_no_delete BEFORE DELETE ON scene_reads
BEGIN SELECT RAISE(ABORT, 'scene_reads is append-only'); END;
