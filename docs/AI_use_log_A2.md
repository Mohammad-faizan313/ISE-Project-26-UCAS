# AI-Use and Source-Verification Log — ISE-A2

**Preparation date:** 12 October 2026  
**Project:** Same clinic appointment project continued from ISE-A1.

## AI tool and tasks

- **Tool:** ChatGPT (OpenAI).
- **Tasks:** Explain the assignment brief; carry A1 project terminology into A2; help draft domain concepts, candidate state/process rules, a data dictionary, invariant counterexamples, test code, report structure and reproducibility instructions; assist with locating publicly available contextual sources.
- **Accepted suggestions:** Keep the focus on non-emergency outpatient scheduling; separate appointment state from queue-ticket state; use a server-authoritative timestamp and explicit time-zone handling; treat a booking as distinct from confirmed arrival; keep medical records outside the model; use synthetic examples for tests; make the arrival-window boundary and no-show policy explicit.
- **Rejected or constrained suggestions:** No target-clinic no-show rate, queue-wait measurement, staff interview, pilot, user research or effectiveness claim was invented. The 15-minute grace period is labelled a configurable example, not a real policy. The data-retention section does not claim a universally applicable duration; clinic, legal and institutional approval are required.

## Verification actually performed

- The reference-model unit tests were run with Python in this environment on 12 October 2026. The captured output reports 36 passing tests. Reproduction command: `python -m unittest discover -s tests -v`.
- Public-source links and relevant subject matter were checked for the reference list in `evidence/a2_source_notes.md`; these sources provide context but do not validate a specific clinic.
- Model examples were checked against the reference rule and test expectations. This is a desk-based specification walkthrough, not a clinic walkthrough or independent stakeholder review.

## Limitations and outstanding external validation

The student must understand and be able to defend the specification and AI contribution. No external clinic representative reviewed this model, and no patient data was used. The proposed workflow, time-window boundary, grace interval, role permissions, retention/deletion schedule and operational exception policy require confirmation with an actual clinic and applicable local requirements before implementation or deployment. The current test suite checks a reference model; it does not prove security, privacy compliance, queue fairness or clinical effectiveness.
