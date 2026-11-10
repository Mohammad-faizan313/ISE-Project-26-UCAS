# AI-use and independent verification log — A4

| Field | Record |
|---|---|
| AI tool | ChatGPT (OpenAI). |
| Tasks assisted | Interpret the A4 brief; carry A1/A2 vocabulary forward; propose a bounded vertical slice; draft FastAPI/SQLite code and test cases; draft interface copy, diagrams, documentation and report structure. |
| Advice accepted | Keep the slice end-to-end but bounded; enforce ownership/role checks server-side; store only password hashes and token hashes; use a transaction and unique appointment-ticket constraint; use idempotency for retry; use `If-Match` for stale staff actions; explicitly test half-open time-window boundaries. |
| Advice rejected/deferred | No biometric identity check, automated no-show, clinical priority queue, diagnosis/triage, real hospital integration, SMS/WeChat message provider or real patient records. These would expand privacy, governance and clinical scope. |
| Independent checks | The local unittest suite was executed; Python compilation was executed; a local Uvicorn smoke test was run against `/health` and `/`; output was retained under `results/a4/`. |
| Limitations | AI assistance contributed to code and report drafting. Automated tests are not a human peer review, user study, security penetration test, clinic validation or production approval. |
