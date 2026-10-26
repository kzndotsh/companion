-- Its own history (ADR 0025): small details of its own past it made up in chat, each with the quote
-- from the message it was said in and that message's frame. An event records what the canon check
-- made of a story (canon, evidence of an earlier one, not canon with the reason) or that the owner
-- retired it; the newest event is its standing, and a story with none waits for the check. The
-- bookmark says how far its own messages have been read. Append-only.

CREATE TABLE stories (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    utterance_id    TEXT NOT NULL REFERENCES utterances (id),
    quote           TEXT NOT NULL,
    claim           TEXT NOT NULL,
    frame           TEXT NOT NULL,
    said_at         TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    recorded_at     TEXT NOT NULL
) STRICT;

CREATE INDEX stories_by_rel ON stories (relationship_id, said_at);

CREATE TABLE story_events (
    id         INTEGER PRIMARY KEY,
    story_id   TEXT NOT NULL REFERENCES stories (id),
    standing   TEXT NOT NULL CHECK (standing IN ('canon', 'evidence', 'not_canon', 'retired')),
    verdict    TEXT,
    of_story   TEXT REFERENCES stories (id),
    reason     TEXT NOT NULL,
    model      TEXT NOT NULL,
    prompt     TEXT NOT NULL,
    at         TEXT NOT NULL
) STRICT;

CREATE INDEX story_events_by_story ON story_events (story_id, id);

CREATE TABLE story_vectors (
    id       INTEGER PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES stories (id),
    model    TEXT NOT NULL,
    vector   BLOB NOT NULL,
    at       TEXT NOT NULL
) STRICT;

CREATE TABLE story_reads (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    upto_at         TEXT NOT NULL,
    upto_id         TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE TRIGGER stories_no_update BEFORE UPDATE ON stories
BEGIN SELECT RAISE(ABORT, 'stories is append-only'); END;
CREATE TRIGGER stories_no_delete BEFORE DELETE ON stories
BEGIN SELECT RAISE(ABORT, 'stories is append-only'); END;
CREATE TRIGGER story_events_no_update BEFORE UPDATE ON story_events
BEGIN SELECT RAISE(ABORT, 'story_events is append-only'); END;
CREATE TRIGGER story_events_no_delete BEFORE DELETE ON story_events
BEGIN SELECT RAISE(ABORT, 'story_events is append-only'); END;
CREATE TRIGGER story_vectors_no_update BEFORE UPDATE ON story_vectors
BEGIN SELECT RAISE(ABORT, 'story_vectors is append-only'); END;
CREATE TRIGGER story_vectors_no_delete BEFORE DELETE ON story_vectors
BEGIN SELECT RAISE(ABORT, 'story_vectors is append-only'); END;
CREATE TRIGGER story_reads_no_update BEFORE UPDATE ON story_reads
BEGIN SELECT RAISE(ABORT, 'story_reads is append-only'); END;
CREATE TRIGGER story_reads_no_delete BEFORE DELETE ON story_reads
BEGIN SELECT RAISE(ABORT, 'story_reads is append-only'); END;
