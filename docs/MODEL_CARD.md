# Model card

## Intended use
Local research and review of network-flow features compatible with UNSW-NB15. The binary model classifies normal versus attack traffic. A separate multiclass model suggests an attack category. Neither makes a confirmed-incident decision or blocks traffic.

## Data and training
The UNSW-NB15 predefined training CSV contains 175,341 records; the predefined test CSV contains 82,332. The selected files have 42 features, an ID, a binary label, and an attack-category label. All three metadata/target columns are excluded from model inputs. The benchmark was generated from normal activities and synthetic attack behaviors; it is not a sample of the user's current network.

The binary model is selected from three fixed CatBoost configurations using tuning-set average precision. Development splits keep identical feature groups together. Model refit uses fitting+tuning data; an independent validation split selects the attack flag threshold. The multiclass model uses validation early stopping. Native CatBoost artifacts and a feature contract are saved together.

## Evaluation
Read `reports/evaluation.md` and `reports/evaluation.json` for actual measured results, false-positive rate, rare-class performance, and duplicate audit. The full test split and test rows without training-feature matches are both reported. `reports/test_predictions.csv` provides row-level outcomes.

## Limitations
- Unseen benchmark records are not necessarily unseen attack types or independent network sessions.
- The CSVs do not provide reliable session/temporal keys for that stronger split.
- Rare classes have small test support, so their metrics are uncertain.
- Validation and test distributions differ; validation false-alarm budgets may not transfer.
- Attack scores are uncalibrated model probabilities and are not statistical certainty estimates.
- A live network needs matching feature extraction, including history/count features, and local evaluation before operational use.
- Independent category suggestions may be `Normal` even for binary-flagged flows, or suggest attacks below the binary threshold. The UI preserves this disagreement.

## Reproducibility and provenance
Use `scripts/download_data.py` for pinned source URLs and SHA-256 verification; see `data/raw/manifest.json`. Seed is 42. Top-level dependencies are pinned; `requirements-lock.txt` records the full verified environment. Source: https://research.unsw.edu.au/projects/unsw-nb15-dataset. Cite Moustafa and Slay (2015), MilCIS, as requested by the dataset authors.
