-- Things named in memory and the words that refer to each (fetch on mention, shadow). A model lists
-- them once per memory; name_reads marks a memory as read even when it names nothing. Append-only.

CREATE TABLE belief_names (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    terms           TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX belief_names_by_rel ON belief_names (relationship_id, belief_id);

CREATE TABLE name_reads (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX name_reads_by_rel ON name_reads (relationship_id, belief_id);

CREATE TRIGGER belief_names_no_update BEFORE UPDATE ON belief_names
BEGIN SELECT RAISE(ABORT, 'belief_names is append-only'); END;
CREATE TRIGGER belief_names_no_delete BEFORE DELETE ON belief_names
BEGIN SELECT RAISE(ABORT, 'belief_names is append-only'); END;
CREATE TRIGGER name_reads_no_update BEFORE UPDATE ON name_reads
BEGIN SELECT RAISE(ABORT, 'name_reads is append-only'); END;
CREATE TRIGGER name_reads_no_delete BEFORE DELETE ON name_reads
BEGIN SELECT RAISE(ABORT, 'name_reads is append-only'); END;
