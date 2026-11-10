# A4 task contract — Patient check-in to receptionist queue call

## Traceability

| Requirement | Origin | A4 observable result |
|---|---|---|
| Patient can create appointment with an arrival window | A1 problem brief / A2 appointment model | `POST /api/appointments` returns a `CONFIRMED` booking. |
| Arrival is confirmed separately from booking | A1 two-stage proposal | Check-in changes state to `CHECKED_IN` and timestamps arrival. |
| One check-in produces one queue ticket | A2 ticket uniqueness invariant | Unique appointment constraint + idempotent transaction returns a single `WAITING` ticket. |
| Only the owner can check in or read patient booking | A2 privacy/authority boundary | Server derives identity from bearer session and checks patient ownership. |
| Only receptionist sees and calls queue | A2 actor/role boundary | Role guard on queue and call endpoints. |
| Arrival window uses half-open interval | A2 decision table | Start inclusive; end exclusive; fixed-clock boundary tests. |
| Stale staff actions cannot overwrite newer ticket state | A2 state/version concept + A4 concurrency control | `If-Match` required; mismatched version returns 412. |

## Selected slice

Patient sign-in → future appointment creation → check-in inside `[window_start, window_end)` → one `WAITING` queue ticket → receptionist queue listing → version-checked call transitions ticket to `CALLED`.

## Exclusions

No medical advice, diagnosis, triage, emergency routing, no-show automation, billing, medical records, real identity service, external messages, hospital integration or real patient data.

## Acceptance conditions

1. Unauthenticated requests to protected routes return 401.
2. A patient cannot read another patient's appointment or call a ticket.
3. A receptionist can view the queue and call a waiting ticket.
4. A check-in at the start boundary succeeds; one at the end boundary fails.
5. Check-in commits the appointment update, ticket creation and idempotency response together.
6. Same-key retry returns the same ticket; a different key after check-in cannot create a second ticket.
7. A missing or stale `If-Match` version cannot perform a staff call.
8. All A2 and A4 tests execute from the repository root using the documented command.
