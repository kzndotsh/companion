-- A reply is stored as soon as it is written, before Telegram has delivered it. When delivery
-- fails the user never saw it, so it is marked here and left out of what the model reads. The
-- ledger itself stays append-only: this is a new row beside the reply, never a change to it.

CREATE TABLE undelivered (
    utterance_id    TEXT PRIMARY KEY REFERENCES utterances (id),
    relationship_id TEXT NOT NULL,
    reason          TEXT NOT NULL,
    at              TEXT NOT NULL
) STRICT;

CREATE TRIGGER undelivered_no_update BEFORE UPDATE ON undelivered
BEGIN SELECT RAISE(ABORT, 'delivery records are append-only'); END;

CREATE TRIGGER undelivered_no_delete BEFORE DELETE ON undelivered
BEGIN SELECT RAISE(ABORT, 'delivery records are append-only'); END;
