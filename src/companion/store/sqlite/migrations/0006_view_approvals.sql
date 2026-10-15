-- A view the companion expressed reaches the card only once the user has approved it.
-- Append-only like everything else: approval is a fact that was recorded, and retiring the belief
-- ends its effect without erasing that it was approved.

CREATE TABLE view_approvals (
    belief_id   TEXT PRIMARY KEY REFERENCES beliefs (id),
    approved_at TEXT NOT NULL
) STRICT;

CREATE TRIGGER view_approvals_no_update BEFORE UPDATE ON view_approvals
BEGIN SELECT RAISE(ABORT, 'approvals are append-only'); END;

CREATE TRIGGER view_approvals_no_delete BEFORE DELETE ON view_approvals
BEGIN SELECT RAISE(ABORT, 'approvals are append-only'); END;
