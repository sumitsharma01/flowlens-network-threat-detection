# Held-out evaluation

Threshold: 0.668820; validation FPR budget: 5.0%.

| Metric | Full official test | Test without train-feature duplicates |
|---|---:|---:|
| accuracy | 0.9018 | 0.8951 |
| precision | 0.8723 | 0.8578 |
| recall | 0.9627 | 0.9561 |
| f1 | 0.9152 | 0.9043 |
| false_positive_rate | 0.1727 | 0.1707 |
| pr_auc_average_precision | 0.9871 | 0.9830 |

Duplicate audit: `{"train_duplicate_feature_rows": 74301, "test_duplicate_feature_rows": 28386, "test_rows_matching_training_features": 8541, "training_feature_groups_with_conflicting_labels": 229}`.

Confusion matrix (rows true normal/attack, columns predicted normal/attack):

```json
[[30610, 6390], [1692, 43640]]
```

These are supervised attack predictions on benchmark flow features, not proof of zero-day detection or live-network performance.
The threshold is chosen on validation data; its false-positive budget is not guaranteed on shifted test or production traffic.
Category suggestions use a separate model and may disagree with binary flags.

Dataset: https://research.unsw.edu.au/projects/unsw-nb15-dataset
Download mirror pinned at Mouwiya/UNSW-NB15-small revision 6f5f54594dfc80c84264aec4c7cc3d9b162f1e2f.
Cite Moustafa and Slay (2015), UNSW-NB15: a comprehensive data set for network intrusion detection systems.

## Separate attack-category classification

| Category | Precision | Recall | F1 | Test rows |
|---|---:|---:|---:|---:|
| Analysis | 0.0000 | 0.0000 | 0.0000 | 677 |
| Backdoor | 0.0414 | 0.0497 | 0.0452 | 583 |
| DoS | 0.4361 | 0.0827 | 0.1390 | 4089 |
| Exploits | 0.5778 | 0.9030 | 0.7047 | 11132 |
| Fuzzers | 0.3202 | 0.6150 | 0.4211 | 6062 |
| Generic | 0.9992 | 0.9654 | 0.9820 | 18871 |
| Normal | 0.9628 | 0.7586 | 0.8486 | 37000 |
| Reconnaissance | 0.8960 | 0.8135 | 0.8528 | 3496 |
| Shellcode | 0.3964 | 0.6931 | 0.5043 | 378 |
| Worms | 0.7500 | 0.1364 | 0.2308 | 44 |

Multiclass macro-F1: 0.4728. Category suggestions are separate from the binary flag decision.
