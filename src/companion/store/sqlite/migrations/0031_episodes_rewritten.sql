-- An episode's line can be written again under a newer prompt: the newest row for a stretch wins and
-- the older ones are kept. So the one-row-per-stretch index goes.

DROP INDEX episodes_by_span;
CREATE INDEX episodes_by_span ON episodes (relationship_id, first_id, at);
