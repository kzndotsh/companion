-- Each of their messages, by its id on the surface it came from, and the turn it belongs to, the
-- way `sent_messages` keeps the companion's: a reply, a reaction or an edit that points at one of
-- their messages can be found again. Kept from 2026-10-27; earlier messages have no id.

CREATE TABLE received_messages (
    relationship_id TEXT NOT NULL,
    channel         TEXT NOT NULL,
    message_id      TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    at              TEXT NOT NULL,
    PRIMARY KEY (relationship_id, channel, message_id)
);
