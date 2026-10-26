-- Each message that carried part of a reply, by its id on the surface that sent it, and the turn it
-- belongs to, so a /flag or /fav sent as a reply to one of them marks that turn. A split reply has
-- several rows for one turn.

CREATE TABLE sent_messages (
    relationship_id TEXT NOT NULL,
    channel         TEXT NOT NULL,
    message_id      TEXT NOT NULL,
    turn_id         TEXT NOT NULL,
    at              TEXT NOT NULL,
    PRIMARY KEY (relationship_id, channel, message_id)
);
