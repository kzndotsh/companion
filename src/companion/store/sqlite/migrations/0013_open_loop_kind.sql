-- What kind of thing a loop is decides when and how to reach out: a follow-up is asked about the
-- morning after ("how did it go?"), a celebration is marked on the day ("happy birthday"), and
-- encouragement is a word the morning of, before it starts. Loops recorded before this are follow-ups.

ALTER TABLE open_loops ADD COLUMN kind TEXT NOT NULL DEFAULT 'follow_up'
    CHECK (kind IN ('follow_up', 'celebrate', 'encourage'));
