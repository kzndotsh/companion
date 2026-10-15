-- What the fast loop was given each turn. Prefixes are content-addressed and stored once.

CREATE TABLE prefixes (
    sha256           TEXT PRIMARY KEY CHECK (length(sha256) = 64),
    system           TEXT NOT NULL,
    tools_json       TEXT NOT NULL CHECK (json_valid(tools_json)),
    estimated_tokens INTEGER NOT NULL
) STRICT;

CREATE TRIGGER prefixes_no_update BEFORE UPDATE ON prefixes
BEGIN SELECT RAISE(ABORT, 'a prefix is content-addressed and immutable'); END;

CREATE TRIGGER prefixes_no_delete BEFORE DELETE ON prefixes
BEGIN SELECT RAISE(ABORT, 'a prefix is content-addressed and immutable'); END;

CREATE TABLE turn_requests (
    turn_id         TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    prefix_sha256   TEXT NOT NULL REFERENCES prefixes (sha256),
    volatile        TEXT NOT NULL,
    request_sha256  TEXT NOT NULL CHECK (length(request_sha256) = 64),
    model           TEXT,
    at              TEXT NOT NULL
) STRICT;

CREATE TRIGGER turn_requests_no_update BEFORE UPDATE ON turn_requests
BEGIN SELECT RAISE(ABORT, 'turn requests are append-only'); END;

CREATE TRIGGER turn_requests_no_delete BEFORE DELETE ON turn_requests
BEGIN SELECT RAISE(ABORT, 'turn requests are append-only'); END;
