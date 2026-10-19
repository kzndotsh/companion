# 0002. The ledger never deletes

**Status:** accepted 2026-10-15. Records a decision already built (commit 7d81009, extended since).

## Decision

Nothing the companion records is edited or deleted in normal operation. Every table that holds
evidence is append-only, enforced by database triggers that abort `UPDATE` and `DELETE`. That covers:

- the conversation ledger (`utterances`) and belief evidence;
- decisions, turn requests and the prefixes they used;
- flags, favorites, spend, and the log of undelivered replies;
- slow-loop runs, view approvals and checks, callback checks, mood effects;
- open loops, their events and reach-outs (ADR 0015).

Beliefs are never deleted: they are closed by setting `valid_until`, and a closure is final. A
correction is a new row that supersedes the old one.

Every row carries `relationship_id`, and conversational rows carry `session_id` and `turn_id`. One
relationship is one SQLite file, in WAL mode, with a single writer (`BEGIN IMMEDIATE`).

## Why

- The beliefs are derived from the ledger. If the ledger is stable, any belief store can be rebuilt
  from it with better rules, and `companion rebuild` does exactly that.
- Replay needs a past that cannot change. The history before a turn must be the same tomorrow as
  it was when the turn ran, or `companion replay` cannot prove what the model saw.
- An audit trail you can edit is not one.

## Consequences

- Curation is closing, with a logged reason, never deleting. `companion retire` and
  `companion dedupe` work this way, and a rebuild closes the old beliefs only after the new ones
  are in.
- A closed belief is still on disk. Nothing in normal use erases a person's words or the beliefs
  drawn from them.
- **True erasure is not built.** If someone needs their conversation and everything derived from
  it removed, that needs a deliberate, separate tool that is explicit about what it destroys. It
  does not exist yet. Until it does, the honest answer to "can it forget this?" is "it can stop
  using it, not erase it".
- A reply the user never received is not deleted either. It is marked in `undelivered` and left
  out of what the model reads.
- The file grows monotonically. At one person's volume that is not a problem.

## Reverses if

Legal or user requirements demand erasure by default. The design would then need a tombstone
scheme that keeps replay honest while removing content.
