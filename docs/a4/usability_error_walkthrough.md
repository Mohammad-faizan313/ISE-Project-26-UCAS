# A4 representative-task and error walkthrough

**Evidence type:** scripted scenario walkthrough against the prototype/API contract. It is not a moderated study, interview, accessibility audit or clinic trial.

## Tasks

| Persona / task | Steps | Expected feedback | Verification evidence |
|---|---|---|---|
| Patient: book a visit | Sign in as `patient`; enter clinic code and future ISO 8601 window; submit. | Appointment ID and `CONFIRMED` status displayed. | API creation test; UI route smoke check. |
| Patient: confirm arrival | Enter appointment ID and idempotency key during the window; submit. | Queue number and `WAITING` status shown. | Check-in integration test. |
| Patient: retry uncertain request | Submit same appointment and same idempotency key again. | Same ticket returned; no duplicate. | Idempotency replay test. |
| Patient: invalid arrival time | Try before start or exactly at end. | Error message; appointment remains unchanged; no ticket issued. | Fixed-clock boundary tests. |
| Receptionist: call next | Sign in as `reception`; refresh queue; call waiting ticket. | Ticket changes to `CALLED`; version increments. | Staff queue/call tests. |
| Receptionist: stale view | Submit call using old version. | 412 response; refresh queue before retry. | Stale-version integration test. |

## Accessibility and usability limitations

The HTML uses labels, native inputs/buttons and an aria-live status area. This is a basic implementation choice, not evidence of conformance to WCAG. No screen-reader test, keyboard-only audit, representative patient recruitment, timed usability study or multilingual usability study was performed. Older adults, users with disabilities, people without smartphones and patients requiring assistance need explicit research before a clinic pilot.

## Error states covered

401 authentication, 403 role/ownership, 404 missing record, 409 invalid state/time/conflict, 412 stale version, 422 malformed input and 428 missing concurrency precondition. The prototype provides a clear text feedback message for UI requests.
