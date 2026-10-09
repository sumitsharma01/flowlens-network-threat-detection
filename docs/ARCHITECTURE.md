# Implemented architecture

This version is an offline flow-feature classifier with a local review dashboard.
It does not capture packets, block traffic, or stream live network events.

Training: version-pinned UNSW-NB15 CSVs → fixed feature validation → feature-group-separated development splits → logistic baseline and three CatBoost candidates → binary refit → independent validation threshold selection → native model artifacts → official held-out evaluation.

A separate multiclass CatBoost model suggests attack categories. Its prediction is displayed independently; it never overrides the binary detector's operating threshold.

Serving: uploaded CSV or held-out sample → shared feature validation → binary/category inference → SQLite review batches → FastAPI endpoints → browser dashboard. The frontend uses static HTML/CSS/JavaScript so local use needs no Node build or third-party CDN. SQLite keeps this single-machine MVP easy to run; PostgreSQL and stream ingestion can be added when required.

## Data boundaries
- `id`, `label`, and `attack_cat` are excluded from input features.
- Optional uploaded labels are used only for post-prediction evaluation.
- Exact feature duplicates are kept together within development splits.
- Test labels do not select hyperparameters, model iterations, or thresholds.
- The report includes the full official test and a subset excluding feature matches with training data.
- These files have no dependable session/timestamp keys for stronger session or temporal separation. Duplicate grouping does not establish independence of all related traffic.

## Operational limits
Run on localhost. The API is unauthenticated and intended for local evaluation. Public hosting requires authentication, tenancy and retention design, deployment controls, and resource limits appropriate to that environment.
Dashboard CSV batches are limited to 10 MiB and 20,000 rows. JSON prediction accepts up to 1,000 records. The CLI handles larger CSVs. Review results and validated feature vectors are persisted locally for native TreeSHAP explanations; original uploaded CSV files are not saved. The local database has no automatic expiry; delete it to clear review history.

Live deployment needs a feature extractor matching all 42 model features, including connection-history features. An arbitrary flow export or PCAP cannot be passed directly to this model.
