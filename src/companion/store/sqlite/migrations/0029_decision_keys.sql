-- A fixed key for each decision, apart from its reason. The reason is the sentence a person reads
-- and may carry details; code that looks past decisions up (a daily cap, "asked already") matches
-- the key. Decisions logged before this have no key and are matched by their reason instead.

ALTER TABLE decisions ADD COLUMN key TEXT;

CREATE INDEX decisions_by_key ON decisions (relationship_id, key, at) WHERE key IS NOT NULL;
