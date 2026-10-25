-- Threads (ADR 0023): open loops become one store for what the companion may bring up, and each
-- row says where it came from. Every row before this is a plan of theirs. The table keeps its name.
-- No CHECK on the value: a new source is added in code (`Source` in features/threads/logic.py),
-- and SQLite cannot widen a CHECK without rebuilding the table.

ALTER TABLE open_loops ADD COLUMN source TEXT NOT NULL DEFAULT 'plan';
