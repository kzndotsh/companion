-- The ledger is append-only. Beliefs are never deleted; they are closed.
-- Every guard the Python types enforce is repeated here so a raw writer cannot bypass it.

CREATE TABLE utterances (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    speaker         TEXT NOT NULL CHECK (speaker IN ('user', 'companion')),
    text            TEXT NOT NULL CHECK (length(text) > 0),
    frame           TEXT NOT NULL CHECK (frame IN ('real', 'play', 'story', 'hypothetical', 'ooc')),
    channel         TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX utterances_by_session ON utterances (relationship_id, session_id, at);
CREATE INDEX utterances_by_turn ON utterances (relationship_id, turn_id);

CREATE TRIGGER utterances_no_update BEFORE UPDATE ON utterances
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;

CREATE TRIGGER utterances_no_delete BEFORE DELETE ON utterances
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;

CREATE TABLE beliefs (
    id              TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    subject         TEXT NOT NULL CHECK (subject IN ('user', 'self', 'relationship', 'world')),
    kind            TEXT NOT NULL CHECK (kind IN
        ('trait', 'state', 'event', 'preference', 'thread', 'boundary', 'tell', 'promise')),
    claim           TEXT NOT NULL CHECK (length(trim(claim)) > 0),
    provenance      TEXT NOT NULL CHECK (provenance IN
        ('stated', 'inferred', 'joked', 'played', 'hypothetical', 'third_party', 'companion_said')),
    speaker         TEXT NOT NULL CHECK (speaker IN ('user', 'companion')),
    frame           TEXT NOT NULL CHECK (frame IN ('real', 'play', 'story', 'hypothetical', 'ooc')),
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    sensitivity     INTEGER NOT NULL DEFAULT 0 CHECK (sensitivity BETWEEN 0 AND 3),
    valid_from      TEXT NOT NULL,
    valid_until     TEXT,
    superseded_by   TEXT REFERENCES beliefs (id),
    recorded_at     TEXT NOT NULL,
    CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CHECK (superseded_by IS NULL OR valid_until IS NOT NULL),
    CHECK ((speaker = 'companion') = (provenance = 'companion_said')),
    CHECK (NOT (frame IN ('play', 'story', 'hypothetical') AND provenance IN ('stated', 'inferred')))
) STRICT;

CREATE INDEX beliefs_current ON beliefs (relationship_id, subject, kind) WHERE valid_until IS NULL;

CREATE TRIGGER beliefs_no_delete BEFORE DELETE ON beliefs
BEGIN SELECT RAISE(ABORT, 'beliefs are closed, never deleted'); END;

CREATE TRIGGER beliefs_core_immutable BEFORE UPDATE ON beliefs
WHEN OLD.id != NEW.id
  OR OLD.relationship_id != NEW.relationship_id
  OR OLD.subject != NEW.subject
  OR OLD.kind != NEW.kind
  OR OLD.claim != NEW.claim
  OR OLD.provenance != NEW.provenance
  OR OLD.speaker != NEW.speaker
  OR OLD.frame != NEW.frame
  OR OLD.valid_from != NEW.valid_from
  OR OLD.recorded_at != NEW.recorded_at
BEGIN SELECT RAISE(ABORT, 'a belief''s claim and origin never change; supersede it'); END;

CREATE TRIGGER beliefs_closure_is_final BEFORE UPDATE ON beliefs
WHEN OLD.valid_until IS NOT NULL
  AND (OLD.valid_until IS NOT NEW.valid_until OR OLD.superseded_by IS NOT NEW.superseded_by)
BEGIN SELECT RAISE(ABORT, 'a closed belief cannot be reopened or re-pointed'); END;

CREATE TABLE belief_evidence (
    belief_id    TEXT NOT NULL REFERENCES beliefs (id),
    utterance_id TEXT NOT NULL REFERENCES utterances (id),
    quote        TEXT NOT NULL CHECK (length(trim(quote)) > 0),
    PRIMARY KEY (belief_id, utterance_id, quote)
) STRICT;

CREATE TRIGGER evidence_quote_is_verbatim BEFORE INSERT ON belief_evidence
WHEN instr((SELECT text FROM utterances WHERE id = NEW.utterance_id), NEW.quote) = 0
BEGIN SELECT RAISE(ABORT, 'quote does not occur in the source utterance'); END;

CREATE TRIGGER evidence_speaker_matches BEFORE INSERT ON belief_evidence
WHEN (SELECT speaker FROM utterances WHERE id = NEW.utterance_id)
  != (SELECT speaker FROM beliefs WHERE id = NEW.belief_id)
BEGIN SELECT RAISE(ABORT, 'evidence speaker differs from the belief''s speaker'); END;

CREATE TRIGGER evidence_frame_matches BEFORE INSERT ON belief_evidence
WHEN (SELECT frame FROM utterances WHERE id = NEW.utterance_id)
  != (SELECT frame FROM beliefs WHERE id = NEW.belief_id)
BEGIN SELECT RAISE(ABORT, 'evidence frame differs from the belief''s frame'); END;

CREATE TRIGGER evidence_no_update BEFORE UPDATE ON belief_evidence
BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;

CREATE TRIGGER evidence_no_delete BEFORE DELETE ON belief_evidence
BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;
