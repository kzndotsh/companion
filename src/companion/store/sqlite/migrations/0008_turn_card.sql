-- The memory card moved out of the user message into its own system block, so a turn records it
-- separately. Turns recorded before this carry the card inside `volatile`, and keep an empty card.

ALTER TABLE turn_requests ADD COLUMN card TEXT NOT NULL DEFAULT '';
