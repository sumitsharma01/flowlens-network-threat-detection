# Dataset provenance and measured quality

## What was used

This project uses the predefined UNSW-NB15 training and test CSVs, not the full raw packet archive. The benchmark originated in 2015 at UNSW Canberra, using a mixture of normal activities and generated attack behavior. The official source describes packet capture and flow feature extraction with Argus and Bro tools. See the [official dataset page](https://research.unsw.edu.au/projects/unsw-nb15-dataset).

The selected CSVs contain 45 columns: **42 inputs**, a row identifier, a binary target, and an attack-category target. The raw release has a different feature layout; its larger feature count should not be used to describe these selected files.

| Field | Role |
|---|---|
| `label` | Binary target: 0 normal, 1 attack |
| `attack_cat` | Multiclass target and post-hoc evaluation metadata |
| `id` | Record identifier, excluded from input |
| `proto`, `service`, `state` | Categorical inputs |
| Remaining 39 inputs | Numeric flow, packet, timing and connection-history features |

Neither target is used as an input. Connection-history fields require matching extraction context for live deployment. Detailed field descriptions are in [data/readme.md](../data/readme.md); the authoritative feature construction is documented by the source authors.

## Exact files and integrity

The download mirror is revision-pinned at `Mouwiya/UNSW-NB15-small`, revision `6f5f54594dfc80c84264aec4c7cc3d9b162f1e2f`. Checksums establish the identity of these mirror files; they are not an independent certification of labels. The source data is fetched through [the mirror](https://huggingface.co/datasets/Mouwiya/UNSW-NB15-small/tree/6f5f54594dfc80c84264aec4c7cc3d9b162f1e2f).

- `UNSW_NB15_training-set.csv`: 175,341 rows; SHA-256 `bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa`.
- `UNSW_NB15_testing-set.csv`: 82,332 rows; SHA-256 `734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559`.

## Measured audit

| Check | Training | Test |
|---|---:|---:|
| Rows | 175,341 | 82,332 |
| Missing input values | 0 | 0 |
| Nonfinite numeric values | 0 | 0 |
| Negative numeric values | 0 | 0 |
| Binary/category label disagreements | 0 | 0 |
| Duplicate prepared-feature rows | 74,301 | 28,386 |
| Unique prepared-feature groups | 101,040 | 53,946 |
| Groups with conflicting binary labels | 229 | 6 |
| Rows in those conflicting groups | 940 | 14 |

Duplicate fractions: **42.38% training**, **34.48% test**. There are **8,541 test rows (10.37%)** whose prepared features match training records. IDs and targets are excluded when identifying matches; numbers use the exact normalized representation consumed by the model.

Conflicting labels on identical selected features do not establish that labels are erroneous: missing context may distinguish the underlying traffic. They do show that this feature representation cannot distinguish those records perfectly. We keep original row labels and disclose the ambiguity.

## Class balance and sample support

| Category | Training rows | Test rows |
|---|---:|---:|
| Normal | 56,000 | 37,000 |
| Generic | 40,000 | 18,871 |
| Exploits | 33,393 | 11,132 |
| Fuzzers | 18,184 | 6,062 |
| DoS | 12,264 | 4,089 |
| Reconnaissance | 10,491 | 3,496 |
| Analysis | 2,000 | 677 |
| Backdoor | 1,746 | 583 |
| Shellcode | 1,133 | 378 |
| Worms | 130 | 44 |

Attack prevalence changes from **68.06%** in training to **55.06%** in test. Rare categories, such as Worms (130 training / 44 test), have small support; a high measured detection rate is not a precise population guarantee. Overall accuracy and weighted averages can hide weak rare-category classification.

## Quality assessment and safeguards

**Useful for reproducible research; insufficient by itself for operational validation.** The files pass these structural checks but have material statistical limitations: repeated feature records, overlap between partitions, ambiguous selected-feature groups, imbalanced categories, and changes in traffic composition. Their age and generated attack setting also limit claims about current production networks.

- Feature-group-separated fitting/tuning/threshold-validation splits keep exact duplicates together within development data. Nominal 60/20/20 proportions apply to groups, not rows.
- The supplied official test remains separate. An additional 73,791-row test subset excludes training feature matches and yields binary F1 90.43%.
- No dependable session or time keys support a stronger temporal/session split here. Exact-match separation does not guarantee independence of related traffic.
- The binary validation FPR is 4.98%, while test FPR is 17.27%. This demonstrates limited transfer of the selected operating point, without proving any single cause.
- Separate attack-category classification has macro-F1 47.28%, including poor results on several rare categories. It is explicitly experimental.

## Reproduce the quality report

```bash
python scripts/download_data.py
python -m scripts.audit_dataset
```

The audit writes [dataset_quality.json](../reports/dataset_quality.json), which also drives the dashboard Dataset quality page. [Evaluation results](../reports/evaluation.md) and [the model card](MODEL_CARD.md) document model behavior separately from data cleanliness.

## Usage terms and attribution

The [official source](https://research.unsw.edu.au/projects/unsw-nb15-dataset) permits academic research use and states that commercial use should be agreed with the authors. Repository code licensing does not relicense the dataset. The source requests citation of the following works; consult its current terms before using the data outside this research project.

1. Moustafa and Slay (2015), [UNSW-NB15: a comprehensive data set for network intrusion detection systems](https://ieeexplore.ieee.org/document/7348942), MilCIS.
2. Moustafa and Slay (2016), *The evaluation of Network Anomaly Detection Systems: Statistical analysis of the UNSW-NB15 data set and comparison with KDD99*, Information Security Journal.
3. Moustafa et al. (2017), *Novel geometric area analysis technique for anomaly detection using trapezoidal area estimation on large-scale networks*, IEEE Transactions on Big Data.
4. Moustafa et al. (2017), *Big data analytics for intrusion detection system: statistical decision-making using finite Dirichlet mixture models*, Data Analytics and Decision Support for Cybersecurity.
5. Sarhan, Layeghy, Moustafa and Portmann (2020/2021 proceedings), [NetFlow Datasets for Machine Learning-Based Network Intrusion Detection Systems](https://arxiv.org/abs/2011.09144).
