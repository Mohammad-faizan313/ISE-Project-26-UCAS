# ADR-001: Enforce queue-ticket uniqueness at an atomic persistence boundary

- Status: Accepted as the target integration decision at A3; implemented in the A4 prototype using SQLite constraints and a transaction.
- Context: A2's pure reference model can inspect a supplied list and detect duplicate active tickets. It cannot prevent two simultaneous web requests from both passing an in-memory pre-check before either request persists a ticket.

## Alternatives

| Alternative | Benefits | Risks / drawbacks |
|---|---|---|
| A. Application-only pre-check | Minimal infrastructure; easy to unit test; keeps pure model simple. | A race can occur between checking and inserting; no durable uniqueness; retries may create duplicates. |
| B. Transaction + database uniqueness + idempotency | Atomic state change; durable one-ticket-per-appointment constraint; safe replay for an uncertain retry. | Adds schema and transaction complexity; requires integration tests and operational database care. |

## Decision

Choose B for the integrated slice. Keep pure model guards as specification aids, but enforce durable uniqueness with a unique `tickets.appointment_id`, unique clinic/date/queue-number key, a transaction around check-in and ticket creation, and an idempotency record keyed by patient and request key.

## Consequences

Positive: a check-in write and ticket creation commit together; duplicate requests with the same key replay the same result; different keys cannot create another ticket after the appointment has moved out of `CONFIRMED`.

Trade-offs: database lock contention and transaction errors must be handled; production deployment would require further concurrency/load and backup/restore tests. The A4 prototype uses SQLite and does not claim production-scale suitability.
