# ISE-A2 Model Walkthrough Record

**Walkthrough type:** Desk-based walkthrough against the proposed domain model and deterministic reference implementation.  
**Date:** 12 October 2026.  
**Participants:** AI-assisted authoring and test execution only; no clinic staff, patients, or external reviewer participated.  
**Boundary:** This record demonstrates a model-based walkthrough; it is not evidence of a real-clinic observation or stakeholder validation.

| ID | Scenario | Expected model behaviour | Verification evidence | Outcome |
|---|---|---|---|---|
| MW-01 | Patient checks in exactly at window start (09:00) | Accept check-in for a confirmed booking | `test_start_boundary_accepted` | Pass |
| MW-02 | Patient attempts check-in one minute before window start | Return `TOO_EARLY`; do not issue a ticket | `test_too_early` | Pass |
| MW-03 | Patient arrives at exact window end (11:00) | Route to late-arrival review because the window is half-open | `test_window_end_routes_to_late_review` | Pass |
| MW-04 | Grace period ends at 11:15 in the configured synthetic example | Mark as eligible for staff no-show reconciliation, not automatically absent | `test_grace_threshold_makes_no_show_eligible` | Pass |
| MW-05 | Cancelled booking attempts check-in | Reject the request | `test_cancelled_rejected` | Pass |
| MW-06 | Same appointment would receive a second active ticket | Invariant checker flags a violation; ticket issuance check disallows a duplicate | `test_two_active_tickets_for_one_booking` and `test_ticket_issuance_allowed_once_after_checkin` | Pass |
| MW-07 | No-show attempted before grace threshold or by a patient role | Disallow no-show state change | `test_before_threshold_not_allowed`, `test_unauthorized_role_not_allowed` | Pass |
| MW-08 | Ticket is already finished or withdrawn and receives a new call transition | Reject illegal state transition | `test_finished_to_waiting_forbidden`, `test_withdrawn_is_terminal` | Pass |
| MW-09 | Timestamp is timezone-naive or window has no positive duration | Reject invalid time-window data | I1 tests | Pass |
| MW-10 | Patient has no smartphone or kiosk/network is unavailable | Model must provide a clinic-approved assisted/manual fallback; fallback operation is a stated design requirement, not implemented or validated by this test suite | Design limitation recorded in report | Open — operational validation required |

## Decisions and unresolved points

- Retained the half-open interval `[start, end)` so adjacent windows do not overlap at the boundary. This is a prototype design choice and must be agreed with the target clinic.
- Kept the 15-minute grace value configurable. It is used only as a deterministic test parameter and is not asserted as local policy.
- No-show is a staff-authorised reconciliation outcome after a threshold; it is not created automatically by the clock.
- The test suite validates a small reference model only. It does not test multi-user concurrency against a database, identity verification, kiosk uptime, accessibility, legal compliance or real queue outcomes.

## Evidence

- `raw_results/a2_test_run.txt` — captured Python unit-test output.
- `raw_results/environment.txt` — runtime/environment details.
- `notebook/a2_model_walkthrough.ipynb` — executable walkthrough and output generation.
- The source code and tests are versioned in this repository.
