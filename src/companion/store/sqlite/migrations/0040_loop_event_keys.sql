-- A fixed key for an open-loop event, apart from its reason, as decisions have had since 0029.
-- Code that counts a kind of event (how often a loop was offered as a note) matches the key; an
-- event written before this has no key and is matched by its reason instead.

ALTER TABLE open_loop_events ADD COLUMN key TEXT;
