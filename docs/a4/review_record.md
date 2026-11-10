# A4 review record and limitations

## Automated review evidence

- 36 A2 domain-model unit tests retained and executed.
- 24 A4 API/integration tests executed.
- Combined command: `python -m unittest discover -s tests -v`.
- Acceptance result from the recorded local run: 60 tests passed, 0 failures, 0 errors.
- Local Uvicorn smoke check: `GET /health` and `GET /` returned HTTP 200.
- API tests use temporary SQLite databases, fixed clocks and synthetic users.

## What was not reviewed

No independent human peer-review record was supplied. No representative user or patient participated in testing. No real clinic workflow was observed. No external security audit, performance/load test, accessibility conformance test, backup/restore test or production deployment validation was performed.

## Review conclusion

The implementation demonstrates a bounded and testable software slice under synthetic local conditions. Further work is required before any real clinic use, including clinic policy approval, real identity integration, privacy/legal review, operational controls, accessibility testing and moderated usability testing.
