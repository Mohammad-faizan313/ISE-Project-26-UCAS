# A4 local rollback and recovery guide

## Scope

This guide applies only to the coursework prototype. It is not a clinical business-continuity or production database recovery plan.

## Application rollback

1. Stop the local Uvicorn process with `Ctrl+C`.
2. Check the current version with `git status --short --branch` and `git log --oneline -5`.
3. To inspect the A3 baseline without changing the current branch, use `git switch --detach ise-a3-v1.0`.
4. To return to the A4 implementation, use `git switch master` (or the default branch configured in the published repository).
5. Do not delete the SQLite file unless the synthetic test data can be discarded. For an intentionally clean local demo, stop the server, back up or remove `clinic_demo.sqlite3`, then restart; the synthetic demo accounts and empty schema are recreated.

## Request-level recovery

- A patient whose check-in response is uncertain should retry the same logical request with the same `Idempotency-Key`. A new key is not a safe substitute for an uncertain retry.
- If the server reports that the appointment is no longer `CONFIRMED`, refresh the appointment and use the clinic's manual assistance path; do not repeatedly submit new keys.
- If a receptionist receives 412, refresh the queue and inspect the latest ticket state/version before attempting any further action.
- A 401 requires a new login. A 403 means the account is not authorised; do not work around the role boundary.

## Production caveat

A real clinic needs reviewed database backups, restore drills, audit history, alerting, incident ownership, kiosk fallback, reconciliation steps, data-retention policy and an approved downtime procedure. None is supplied by this prototype.
