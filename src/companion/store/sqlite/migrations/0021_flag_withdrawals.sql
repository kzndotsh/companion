-- A flag the owner takes back (they meant /fav, or flagged the wrong turn). The flag stays in the
-- ledger; a withdrawal row hides it from the flag list. Append-only.

CREATE TABLE flag_withdrawals (
    id      INTEGER PRIMARY KEY,
    flag_id TEXT NOT NULL REFERENCES flags (id),
    reason  TEXT NOT NULL,
    at      TEXT NOT NULL
) STRICT;

CREATE TRIGGER flag_withdrawals_no_update BEFORE UPDATE ON flag_withdrawals
BEGIN SELECT RAISE(ABORT, 'flag_withdrawals is append-only'); END;
CREATE TRIGGER flag_withdrawals_no_delete BEFORE DELETE ON flag_withdrawals
BEGIN SELECT RAISE(ABORT, 'flag_withdrawals is append-only'); END;
