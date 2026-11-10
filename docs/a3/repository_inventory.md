# A3 repository inventory — frozen A2 baseline

## Snapshot

- Baseline tag: `ise-a2-v1.0`
- Baseline commit: `e8612772f9a145de60bbaf288b43950ae64d59d6`
- Runtime recorded in the A3 report: Python 3.13.5
- Baseline scope: pure Python reference model, unit tests, notebooks, evidence ledger, domain diagrams and assessment documents.

## Observed implementation boundary

The A2 snapshot contains `src/clinic_model.py`, with data classes/enums and pure checks for timezone-aware windows, appointment-state coherence, ticket uniqueness in a supplied collection, no-show eligibility and allowed ticket transitions. `tests/test_clinic_model.py` exercises the model. The snapshot does not contain an HTTP API, browser UI, database adapter, application service or production process entry point.

## Reproduction commands (from the baseline checkout)

```bash
python --version
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

The recorded A3 investigation reports 36 passing tests on Python 3.13.5. This was a model-level verification, not an end-to-end service test.

## Architecture change boundary

A4 introduces the application/UI/persistence boundary in separate `app/` and `static/` directories. The domain reference module remains available in `src/` and its 36 tests remain unchanged. A4 adds 24 HTTP/API integration tests in `tests/test_vertical_slice.py`.

## Limitations

The A2 snapshot contains synthetic test values only. No clinic-specific workflow observation, real patient dataset, load test, production identity provider or external hospital integration is present.
