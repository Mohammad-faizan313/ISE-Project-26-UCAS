# Intelligent Software Engineering — Clinic Appointment Project (A1–A4)

**Project:** Two-Stage Clinic Appointment and Arrival-Confirmation System for non-emergency outpatient care in China.

This repository carries one project through the first four Intelligent Software Engineering assessments:

- **A1 — Problem and stakeholder evidence:** opportunity framing, evidence ledger and stakeholder/workflow context.
- **A2 — Domain model and testable specification:** domain language, state model, invariants, decision table, data dictionary and a deterministic Python reference model.
- **A3 — Repository investigation and reproducible build:** inspection of the A2 snapshot, execution evidence, architectural boundary, risk register and ADR-001.
- **A4 — End-to-end vertical slice and automated verification:** a small FastAPI + SQLite prototype connecting online booking, patient check-in, queue-ticket issuance and receptionist calling.

The system is an educational prototype using synthetic identities and data. It is **not** a production clinic system and must not be used for real patient records or clinical decisions.

## 1. Repository contents

```text
.
├── app/                         # A4 FastAPI application and SQLite service logic
├── static/                      # A4 patient/reception browser interface
├── src/                         # A2 pure domain reference model
├── tests/                       # 36 A2 model tests + 24 A4 API integration tests
├── models/                      # A2 domain/state/event diagrams and A4 architecture maps
├── evidence/                    # A1/A2 source notes and evidence ledger
├── notebook/                    # A1/A2 reproducible analysis/model walkthrough notebooks
├── notebooks/                   # A4 end-to-end verification notebook
├── raw_results/                 # A1/A2 recorded results and environment details
├── results/a3/                  # A3 baseline repository inspection execution records
├── results/a4/                  # A4 test, smoke and environment evidence
├── docs/a3/                     # A3 risk/ADR and repository inventory support
├── docs/a4/                     # A4 task contract, review, rollback and AI-use log
├── report/                      # A1, A2, A3 and A4 Word reports (A1/A2 PDFs included)
├── requirements.txt             # Top-level pinned A4 dependency file
└── requirements-a4.lock         # Full pinned runtime/test dependency set
```

## 2. Environment

Recorded environment for the A4 verification run:

- Python 3.13.5
- FastAPI 0.128.2
- Starlette 0.50.0
- Pydantic 2.13.5
- Uvicorn 0.48.0
- HTTPX 0.28.1
- SQLite supplied by Python's standard library

Python 3.11+ is expected. The exact dependency versions used in the recorded run are in `requirements-a4.lock`.

## 3. Quick start

Create and activate a virtual environment:

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run all A2 and A4 automated tests:

```bash
python -m unittest discover -s tests -v
```

Expected recorded result: **60 tests, 0 failures, 0 errors** (36 A2 domain tests + 24 A4 HTTP/API tests). Runtime may vary by machine. Preserve any differing or failed run rather than overwriting the historical output.

Start the local prototype:

```bash
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in a browser. Health endpoint: `http://127.0.0.1:8000/health`.

### Synthetic demo credentials

| Role | Username | Password |
|---|---|---|
| Patient | `patient` | `PatientDemo!2026` |
| Receptionist | `reception` | `ReceptionDemo!2026` |

These credentials are fixed demonstration fixtures created by the app on first database initialisation. They are **not secrets**, must never be reused outside local coursework, and must be replaced with a proper identity provider and secrets management before any real deployment.

By default, the SQLite database is `clinic_demo.sqlite3` in the repository root. To use another location, set `ISE_A4_DB` before starting the server:

```bash
# Linux/macOS
export ISE_A4_DB=/tmp/clinic-demo.sqlite3
# Windows PowerShell
# $env:ISE_A4_DB = "$env:TEMP\clinic-demo.sqlite3"
```

## 4. Implemented A4 workflow

1. Patient signs in with a synthetic account.
2. Patient creates a future appointment with clinic code and a timezone-aware arrival window.
3. Patient checks in while server time is within `[window_start, window_end)`.
4. The server transaction changes appointment state to `CHECKED_IN`, creates one `WAITING` queue ticket and saves the idempotent response.
5. An authorised receptionist views the active queue.
6. Receptionist calls a `WAITING` ticket using `If-Match` to prevent a stale version from overwriting a newer state.

### Main API routes

| Method | Route | Role / purpose |
|---|---|---|
| `GET` | `/` | Public browser UI |
| `GET` | `/health` | Basic health response |
| `POST` | `/api/login` | Create bearer session |
| `POST` | `/api/appointments` | Patient creates appointment |
| `GET` | `/api/appointments/{id}` | Owner or receptionist reads appointment |
| `POST` | `/api/appointments/{id}/check-in` | Patient confirms arrival; requires `Idempotency-Key` |
| `GET` | `/api/staff/queue?clinic_code=...` | Receptionist views queue |
| `POST` | `/api/staff/tickets/{id}/call` | Receptionist calls ticket; requires `If-Match` |

## 5. Verification evidence

- `results/a3/` documents the inspected A2 baseline and its 36-test execution.
- `results/a4/` documents the A4 runtime, 60-test regression run, and live-server smoke test.
- `notebooks/a4_vertical_slice_walkthrough.ipynb` is an executable scenario walkthrough using synthetic data.
- `docs/a4/usability_error_walkthrough.md` is a scripted task walkthrough, not real participant research.

The recorded test pass demonstrates conformance to the implemented synthetic examples. It does not establish that the design reduces real clinic waiting times, no-shows, or staff workload. It is not a substitute for a real clinic policy review, security assessment, accessibility review, moderated user study, load test, backup/restore test or production integration test.

## 6. Safety, privacy and scope limits

Excluded: diagnosis, prescriptions, emergency triage, medical records, insurance, payments, SMS/WeChat messaging, external hospital systems, automated no-show classification and clinical queue prioritisation. No real patient data is included.

Before a real deployment, a clinic would need to approve booking and late-arrival policies, identify a lawful data-processing basis, define retention/deletion, review accessibility and language requirements, implement hardened identity/session controls, secure deployment and monitoring, backup/restore, audit trails, incident response and a manual fallback for kiosk/network outage.

## 7. Git history and tags

The repository preserves the A1/A2 Git history and adds a tagged progression through A3/A4:

- `ise-a1-v1.0`
- `ise-a2-v1.0`
- `ise-a3-v1.0`
- `ise-a4-v1.0`

The repository is locally versioned. To publish it, create an empty repository under your GitHub account and run:

```bash
git remote add origin https://github.com/<YOUR-ACCOUNT>/<YOUR-REPOSITORY>.git
git push -u origin master
git push origin --tags
```

Then use your real GitHub repository URL and the relevant tag/commit in the matching course-platform task. Do not submit a placeholder URL.

## 8. AI-use disclosure

AI assistance was used to help draft and organise parts of the project, including code, tests, diagrams, documentation and report structure. The repository includes a task-level log in `docs/a4/AI_use_log_A4.md`. Test and smoke outputs in `results/` were generated by local execution in the package-building environment. No peer review, representative-patient usability study, clinic trial or production deployment is claimed.
