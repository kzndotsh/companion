-- Groups of memories about one thing that would read better as one (ADR 0019): the members, the
-- merged wording a model proposed, and the owner's answer. Nothing is merged without the owner.
-- Append-only.

CREATE TABLE merge_proposals (
    id              INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    members         TEXT NOT NULL,
    claim           TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE TABLE merge_answers (
    id          INTEGER PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES merge_proposals (id),
    answer      TEXT NOT NULL,
    at          TEXT NOT NULL
) STRICT;

CREATE TRIGGER merge_proposals_no_update BEFORE UPDATE ON merge_proposals
BEGIN SELECT RAISE(ABORT, 'merge_proposals is append-only'); END;
CREATE TRIGGER merge_proposals_no_delete BEFORE DELETE ON merge_proposals
BEGIN SELECT RAISE(ABORT, 'merge_proposals is append-only'); END;
CREATE TRIGGER merge_answers_no_update BEFORE UPDATE ON merge_answers
BEGIN SELECT RAISE(ABORT, 'merge_answers is append-only'); END;
CREATE TRIGGER merge_answers_no_delete BEFORE DELETE ON merge_answers
BEGIN SELECT RAISE(ABORT, 'merge_answers is append-only'); END;
