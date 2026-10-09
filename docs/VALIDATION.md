# Delivery validation

Executed on Python 3.13.6, CatBoost 1.2.10, pandas 3.0.6, scikit-learn 1.9.1.

- Downloaded the complete predefined UNSW-NB15 training/test CSVs, verified pinned SHA-256 hashes and row counts (175,341 / 82,332).
- Completed binary candidate selection, binary refit, validation threshold selection, and multiclass training. Training took 1,092.4 seconds on this machine.
- Evaluated the official test without tuning against its outcomes. Binary recall 96.27%, precision 87.23%, F1 91.52%; normal-flow false-positive rate 17.27%.
- Test rows without feature matches to training: 73,791; binary F1 90.43%.
- Separate category classification: accuracy 77.18%, macro-F1 47.28%. Suggestions are experimental, with weak performance on some rare classes.
- Ran `python -m pytest -q`: 13 passed. A framework deprecation warning about TestClient/httpx was emitted; no tests failed or skipped.
- Ran Python compile checks and `node --check frontend/app.js`.
- Ran the prediction CLI on 300 feature-only sample flows: 179 flagged.
- Started the actual localhost FastAPI server and tested in the browser: sample replay, CSV upload (300 scored / 179 flagged), flagged-only filtering, next-page pagination (51–100 of 179), and the real held-out model metrics display.
- Captured `reports/dashboard.jpg` and rendered/inspected `reports/evaluation.png`.
- Docker configuration and CI workflow are provided. Docker execution was not verified because Docker is not installed here; GitHub Actions runs formatting and tests on pushes; see the repository Actions page for the latest remote result.

The implementation and artifacts are local. The initial delivery was local; the repository update publishes source, trained model artifacts, documentation and screenshots. The application is not deployed publicly.

## Notebook addition

- Added a 33-cell commented training/evaluation notebook using shared split and model-building modules.
- Executed the full saved-model evaluation mode on the original train/test CSVs, with assertions that split/threshold/test metrics reproduce the supplied report.
- Executed the optional training path separately with 500 training records and a 10-tree budget as a smoke check. This does not represent a new full-dataset training result.
- Exported a standalone HTML preview with embedded tables and plots.
- Regression tests after the shared-module refactor: 14 passed, including duplicate-group separation.
- The supplied model files and their evaluation outcomes were preserved.

## Explainability and quality update

- Native TreeSHAP reconstructs each binary raw score, with sigmoid agreement and threshold agreement checked against actual predictions.
- API tests cover saved-feature explanations, mismatched model versions, payload limits, and legacy database migration without inventing explanations for older batches.
- Measured dataset audit: no missing input values, 74,301 duplicated training feature rows, 8,541 test rows matching training, and 229 conflicting-label training feature groups affecting 940 rows.
- Re-executed all 19 notebook code cells, including quality measurements and a false-positive explanation; model artifacts were preserved.
- Executed 18 tests successfully after the changes.
- Checked desktop readability at 1440 × 1000 and the narrow browser panel (517 px), with no horizontal page overflow. Captured actual overview, explanation, evaluation and quality screenshots; temporary viewport settings were reset.
- Formatting: Black for Python, Prettier for browser source. CI runs formatting and artifact integration tests; full training is not rerun by CI.
