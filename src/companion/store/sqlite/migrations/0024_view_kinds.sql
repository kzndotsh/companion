-- What kind of thing each of the companion's views is (ADR 0020): taste (its lore), stance, rule, self
-- or lived. A model labels, code reads only taste as lore. A view can be labelled again; the newest row
-- wins. Append-only.

CREATE TABLE view_kinds (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    belief_id       TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('taste', 'stance', 'rule', 'self', 'lived')),
    model           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE INDEX view_kinds_by_belief ON view_kinds (relationship_id, belief_id, id);

CREATE TRIGGER view_kinds_no_update BEFORE UPDATE ON view_kinds
BEGIN SELECT RAISE(ABORT, 'view_kinds is append-only'); END;
CREATE TRIGGER view_kinds_no_delete BEFORE DELETE ON view_kinds
BEGIN SELECT RAISE(ABORT, 'view_kinds is append-only'); END;
