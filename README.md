# Cloud AI Network Monitor

A working supervised network intrusion classifier trained on UNSW-NB15, with a local dashboard for scoring CSV flow features, reviewing flagged traffic, and inspecting held-out model performance.

## Explainability, data quality, and screenshots

Use **Explain** beside a flow to inspect the features that raised or lowered its attack score. Native CatBoost TreeSHAP contributions reconstruct the raw model score; supplied labels expose false positives rather than treating explanations as proof of an attack.

- [Explainability guide](docs/EXPLAINABILITY.md): contribution units, reconstruction, API, and limitations.
- [Dataset quality report](docs/DATASET.md): source, exact files/checksums, missing values, duplicate overlap, conflicting labels, class support, and usage terms.
- [Screenshot walkthrough](docs/SCREENSHOTS.md): actual dashboard, explanation, model evaluation, and dataset audit views.
- [Commented notebook](notebooks/network_traffic_training.ipynb): shared training pipeline, evaluation, SHAP, and data-quality discussion.

## Measured results

Official held-out test: **96.27% attack recall, 87.23% precision, 91.52% F1, 90.18% accuracy**. The normal-traffic false-positive rate is **17.27%**, versus 4.98% on validation. This prototype needs local-network validation and false-alarm improvement before operational use. The test was not used to retune the threshold.

The separate category classifier has **47.28% macro-F1** and struggles with several rare categories; its suggestions are explicitly experimental. Full diagnostics are in `reports/evaluation.md`. The duplicate-free-from-training test subset has **90.43% binary F1**.

## What it does
- CatBoost binary classification: normal versus attack, with a validation-selected flag threshold.
- Separate CatBoost multiclass model: normal or one of nine attack categories.
- Strict, shared 42-feature contract; targets and row IDs never enter the models.
- Official held-out test evaluation, duplicate audit, per-attack detection rates, and a novel-feature subset report.
- CSV upload, real held-out sample replay, persisted SQLite batches, filtered/paginated review, and CSV export.
- Local API and responsive dashboard, with no external frontend services.

This is flow-feature classification. It does not capture live packets or establish zero-day detection quality.

## Run locally
Python 3.13 is the verified runtime. From this repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and select **Replay sample**, or upload `data/sample/flows.csv`. Open http://127.0.0.1:8000/docs for the API.

The delivered project bundle includes trained `.cbm` model files, sample data, and evaluation reports. The repository includes the trained native model files. Retraining is optional; to rebuild the application bundle:

```bash
python scripts/download_data.py
python -m ml.train
```

## Jupyter training walkthrough

`notebooks/network_traffic_training.ipynb` is a commented, step-by-step notebook with data inspection, leakage prevention, duplicate-aware splits, baseline comparison, CatBoost training, threshold selection, held-out evaluation, error examples, and inference. `notebooks/network_traffic_training.html` is an executed preview with embedded tables and charts.

```bash
pip install -r requirements-notebook.txt
python scripts/download_data.py
python -m jupyter lab notebooks/network_traffic_training.ipynb
```

Default `RUN_TRAINING = False` loads the supplied models and recomputes evaluation using the complete train/test CSVs. Set it to `True` to rerun the included training stages. Optional exports go to `artifacts/notebook-run/`; existing application models are preserved. The notebook shares `ml/splits.py`, `ml/pipeline.py`, and the feature/evaluation helpers with the CLI.

## Train and evaluate

```bash
python scripts/download_data.py
python -m ml.train --iterations 600 --max-fpr 0.05
```

Downloads are pinned to a public mirror revision; the downloader checks expected row counts and SHA-256 hashes. Dataset authors/source: https://research.unsw.edu.au/projects/unsw-nb15-dataset. Cite Moustafa and Slay, 2015, *UNSW-NB15: a comprehensive data set for network intrusion detection systems* (MilCIS). Dataset usage remains subject to the source terms; the repository code license does not relicense it.

Training uses the official 175,341-row training file, and testing uses the separate 82,332-row file. Unique feature groups create approximately 60% fitting / 20% tuning / 20% calibration splits within the training file, keeping identical features together. A logistic regression baseline and three CatBoost binary configurations are evaluated on tuning data. CatBoost selection uses average precision; binary refit uses fitting+tuning data with the selected iteration count. The independent calibration split chooses the highest-recall threshold within the requested normal-flow false-positive budget. A separate category model uses validation early stopping.

The official test is evaluated only after models and threshold are frozen. It is never mixed into training or tuning. The report also measures test rows without feature matches to training. Do not repeatedly tune against reported test results.

A validation false-positive budget is not a guarantee on test or deployment traffic. Scores are not calibrated confidence estimates. There is no reliable temporal/session separation in these CSVs; exact-duplicate grouping only addresses one form of leakage.

Outputs:
- `artifacts/binary.cbm`, `category.cbm`, `metadata.json`
- `reports/evaluation.md` and detailed `evaluation.json`
- `reports/test_predictions.csv` with actual labels and decisions
- `data/raw/manifest.json` with pinned URLs/checksums

## Predict unseen flows

```bash
python -m ml.predict data/sample/flows.csv --output reports/new-predictions.csv
```

Provide the 42 columns listed in `ml/features.py` or `/api/model-info`. `id`, `label`, and `attack_cat` are optional metadata and ignored during inference. Extra or missing feature columns, missing categories, negative/nonfinite numerical values, and malformed input are rejected. New categorical values are supported. No learned scaling is required for the tree models; numerical validation and categorical whitespace normalization are identical at training and inference.

Binary flags and category suggestions are independent and may disagree. A flag warrants review; it does not establish a confirmed incident. Live use requires a compatible feature extractor, including connection-history features.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover target leakage prevention, invalid inputs, threshold ties/budgets, actual artifact scoring, JSON/CSV inference consistency, batch persistence, exports, SHAP reconstruction, stale-version protection, and legacy database migration. The trained files and sample data are included, so CI runs artifact integration tests without downloading the full dataset.

## Docker

With trained artifacts present:

```bash
docker compose up --build
```

Open http://127.0.0.1:8000. Review history uses a named volume. The Docker setup is provided; see the delivery report for which checks were actually executed.

## Layout

```text
backend/       FastAPI API, SQLite review history
frontend/      Static dashboard
ml/            Features, splits, model builders, evaluation, inference, SHAP
scripts/       Version-pinned dataset download
artifacts/     Trained native CatBoost files and metadata
reports/       Real evaluation and held-out predictions
data/sample/   Real held-out sample, labeled and feature-only
tests/         Unit and integration checks
docs/          Implemented architecture and API
```

Run locally: the server has no authentication and no automatic history expiry. Original uploaded files are not persisted; validated feature vectors are retained in the review database for explanations. The dashboard accepts at most 20,000 flows / 10 MiB per batch; use the CLI for larger files. Kafka, PostgreSQL, and Kubernetes from the original design remain future extensions, after a validated ingestion use case exists.
