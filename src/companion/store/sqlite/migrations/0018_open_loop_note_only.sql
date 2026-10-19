-- A same-day plan ("exam in two hours", "laundry's almost done") is kept as a note-only loop: it is
-- never a reach-out, only a quiet note when they next write a few hours on (J15). Loops recorded
-- before this are not note-only.

ALTER TABLE open_loops ADD COLUMN note_only INTEGER NOT NULL DEFAULT 0 CHECK (note_only IN (0, 1));
