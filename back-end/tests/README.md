# Backend Test Suite

Automated test suites for the PARAKH risk engine, classifier, ML model, and system invariants.

## Test Modules

- `test_engine.py`: 22 unit tests covering the 6-rule scoring engine, exact mathematical boundaries, and tier classifications.
- `test_callanalyzer.py`: 7 unit tests covering coercive call pattern matching, confidence calibration, and edge cases.
- `test_forest.py`: 4 unit tests covering Isolation Forest feature extraction, normalization, and parity logic.
- `test_parity.py`: 6 integration tests verifying system invariants, database bootstrapping, and scam-beats-soft guarantees.

## Running Tests

```bash
python -m pytest -v
```
