-- Per-relationship settings, and the result of checking a view against what the user has asked for.
-- Both are append-only logs. The newest row for a key (or a belief) is the current answer, and the
-- earlier rows stay as the record of what was true when.

CREATE TABLE settings_log (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX settings_by_key ON settings_log (relationship_id, key, id);

CREATE TRIGGER settings_no_update BEFORE UPDATE ON settings_log
BEGIN SELECT RAISE(ABORT, 'settings are append-only'); END;

CREATE TRIGGER settings_no_delete BEFORE DELETE ON settings_log
BEGIN SELECT RAISE(ABORT, 'settings are append-only'); END;

CREATE TABLE view_checks (
    id        INTEGER PRIMARY KEY,
    belief_id TEXT NOT NULL REFERENCES beliefs (id),
    conflicts INTEGER NOT NULL CHECK (conflicts IN (0, 1)),
    detail    TEXT NOT NULL CHECK (json_valid(detail)),
    at        TEXT NOT NULL
) STRICT;

CREATE INDEX view_checks_by_belief ON view_checks (belief_id, id);

CREATE TRIGGER view_checks_no_update BEFORE UPDATE ON view_checks
BEGIN SELECT RAISE(ABORT, 'view checks are append-only'); END;

CREATE TRIGGER view_checks_no_delete BEFORE DELETE ON view_checks
BEGIN SELECT RAISE(ABORT, 'view checks are append-only'); END;
