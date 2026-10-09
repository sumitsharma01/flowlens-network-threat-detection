"""Measure quality of the exact feature representation used by the models."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.features import FEATURES, CATEGORICAL, prepare, fingerprints
from ml.predict import ROOT


def main():
    frames = {
        name: pd.read_csv(ROOT / f"data/raw/UNSW_NB15_{name}-set.csv")
        for name in ["training", "testing"]
    }
    hashes = {name: fingerprints(frame) for name, frame in frames.items()}
    result = {
        "dataset": "UNSW-NB15",
        "source": "https://research.unsw.edu.au/projects/unsw-nb15-dataset",
        "input_features": len(FEATURES),
        "categorical_features": CATEGORICAL,
        "feature_definition": "All 42 prepared feature values; excludes id, label and attack_cat",
        "files": json.loads((ROOT / "data/raw/manifest.json").read_text()),
        "splits": {},
    }
    for name, frame in frames.items():
        prepared = prepare(frame)
        group_labels = (
            pd.DataFrame({"hash": hashes[name], "label": frame.label})
            .groupby("hash")
            .label.nunique()
        )
        ambiguous = set(group_labels[group_labels > 1].index)
        numeric = prepared[[c for c in FEATURES if c not in CATEGORICAL]]
        result["splits"][name] = {
            "rows": len(frame),
            "columns": len(frame.columns),
            "feature_missing_values": int(frame[FEATURES].isna().sum().sum()),
            "numeric_nonfinite_values": int((~np.isfinite(numeric)).sum().sum()),
            "numeric_negative_values": int((numeric < 0).sum().sum()),
            "binary_category_label_disagreements": int(
                (frame.attack_cat.eq("Normal") != frame.label.eq(0)).sum()
            ),
            "duplicate_feature_rows": int(hashes[name].duplicated().sum()),
            "duplicate_fraction": float(hashes[name].duplicated().mean()),
            "unique_feature_groups": int(hashes[name].nunique()),
            "conflicting_binary_label_groups": len(ambiguous),
            "rows_in_conflicting_binary_groups": int(
                hashes[name].isin(ambiguous).sum()
            ),
            "attack_fraction": float(frame.label.mean()),
            "class_counts": {
                k: int(v) for k, v in frame.attack_cat.value_counts().items()
            },
        }
    result["test_rows_matching_training"] = int(
        hashes["testing"].isin(set(hashes["training"])).sum()
    )
    result["test_match_fraction"] = result["test_rows_matching_training"] / len(
        frames["testing"]
    )
    result["unseen_test_categories"] = {
        name: sorted(
            set(frames["testing"][name].astype(str))
            - set(frames["training"][name].astype(str))
        )
        for name in CATEGORICAL
    }
    result["quality_assessment"] = (
        "Useful research benchmark; duplicate overlap, conflicting feature labels, rare classes and distribution differences limit operational claims."
    )
    path = ROOT / "reports/dataset_quality.json"
    path.write_text(json.dumps(result, indent=2))
    print("Saved", path)
    print(json.dumps(result["splits"], indent=2))


if __name__ == "__main__":
    main()
