"""Reproducible training. Test outcomes never select a model or threshold."""

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
import catboost
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
)
from ml.evaluate import metrics, choose_threshold
from ml.features import FEATURES, CATEGORICAL, prepare, fingerprints
from ml.splits import development_split
from ml.pipeline import baseline_pipeline, binary_model, category_model

ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=600)
    parser.add_argument("--max-fpr", type=float, default=0.05)
    args = parser.parse_args()
    if not 0 < args.max_fpr < 1:
        parser.error("--max-fpr must be between 0 and 1")
    started = time.time()
    artifacts, reports = ROOT / "artifacts", ROOT / "reports"
    artifacts.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    paths = [
        ROOT / "data/raw" / f"UNSW_NB15_{s}-set.csv" for s in ["training", "testing"]
    ]
    train, test = [pd.read_csv(p) for p in paths]
    assert (
        len(train) == 175341 and len(test) == 82332
    ), "Unexpected official split row counts"
    for frame in [train, test]:
        if not set(frame.label.unique()) <= {0, 1} or frame.label.isna().any():
            raise ValueError("Invalid target labels")
        if not (frame.attack_cat.eq("Normal") == frame.label.eq(0)).all():
            raise ValueError("Inconsistent binary and category labels")
    # Stage 1: validate the fixed feature contract and isolate development groups.
    X, Xt = prepare(train), prepare(test)
    hashes, test_hashes = fingerprints(train), fingerprints(test)
    # One shared split implementation is used by this CLI and the notebook.
    (fit_mask, tune_mask, cal_mask), hashes = development_split(train, SEED)
    print(
        "Development rows:",
        [int(m.sum()) for m in [fit_mask, tune_mask, cal_mask]],
        flush=True,
    )
    candidates = []
    # Stage 2: establish a baseline, then select candidates on tuning data only.
    baseline = baseline_pipeline(SEED)
    baseline.fit(X[fit_mask], train.label[fit_mask])
    bp = baseline.predict_proba(X[tune_mask])[:, 1]
    baseline_tuning = metrics(train.label[tune_mask], bp, 0.5)
    print(
        "Logistic baseline tuning AP:",
        baseline_tuning["pr_auc_average_precision"],
        flush=True,
    )
    for depth, weight in [(6, 1), (8, 1), (8, 2)]:
        model = binary_model(args.iterations, depth, weight, SEED, tuning=True)
        model.fit(
            X[fit_mask],
            train.label[fit_mask],
            cat_features=CATEGORICAL,
            eval_set=(X[tune_mask], train.label[tune_mask]),
            early_stopping_rounds=60,
        )
        score = average_precision_score(
            train.label[tune_mask], model.predict_proba(X[tune_mask])[:, 1]
        )
        entry = {
            "depth": depth,
            "attack_weight": weight,
            "iterations": model.tree_count_,
            "tuning_average_precision": float(score),
        }
        candidates.append(entry)
        print("Candidate:", entry, flush=True)
    winner = max(candidates, key=lambda c: c["tuning_average_precision"])
    # Stage 3: refit without threshold-validation rows; select the operating point.
    binary = binary_model(
        winner["iterations"], winner["depth"], winner["attack_weight"], SEED
    )
    development = fit_mask | tune_mask
    binary.fit(X[development], train.label[development], cat_features=CATEGORICAL)
    cp = binary.predict_proba(X[cal_mask])[:, 1]
    threshold = choose_threshold(train.label[cal_mask], cp, args.max_fpr)
    # Stage 4: train an independent experimental attack-category classifier.
    category = category_model(args.iterations, SEED)
    print("Training attack-category classifier…", flush=True)
    category.fit(
        X[development],
        train.attack_cat[development],
        cat_features=CATEGORICAL,
        eval_set=(X[cal_mask], train.attack_cat[cal_mask]),
        early_stopping_rounds=60,
    )
    binary.save_model(str(artifacts / "binary.cbm"))
    category.save_model(str(artifacts / "category.cbm"))
    # Freeze models and operating point before inspecting held-out outcomes.
    metadata = {
        "model_version": "unsw-catboost-v1",
        "dataset": "UNSW-NB15",
        "features": FEATURES,
        "categorical_features": CATEGORICAL,
        "threshold": threshold,
        "validation_fpr_budget": args.max_fpr,
        "seed": SEED,
        "selected_candidate": winner,
        "category_classes": category.classes_.tolist(),
        "category_iterations": category.tree_count_,
        "score_description": "Uncalibrated CatBoost attack probability; not certainty or novelty score",
        "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "catboost_version": catboost.__version__,
        "python": platform.python_version(),
    }
    metadata["artifact_sha256"] = {
        name: hashlib.sha256((artifacts / name).read_bytes()).hexdigest()
        for name in ["binary.cbm", "category.cbm"]
    }
    bundle_hash = hashlib.sha256(
        json.dumps(
            {"artifacts": metadata["artifact_sha256"], "threshold": threshold},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    metadata["model_version"] = "unsw-v1-" + bundle_hash[:8]
    (artifacts / "metadata.json").write_text(json.dumps(metadata, indent=2))
    # Stage 5: score the reserved test only after all decisions are frozen.
    test_scores = binary.predict_proba(Xt)[:, 1]
    cats = category.predict(Xt).ravel()
    novel = ~test_hashes.isin(set(hashes))
    predictions = (test_scores >= threshold).astype(int)
    per_category = {}
    for name, rows in test.groupby("attack_cat").groups.items():
        per_category[name] = {
            "rows": len(rows),
            "flag_rate": float(predictions[rows].mean()),
        }
    report = {
        "model_version": metadata["model_version"],
        "dataset": metadata["dataset"],
        "protocol": "Official predefined train/test split; feature-group-separated 60/20/20 development splits",
        "threshold": threshold,
        "validation_fpr_budget": args.max_fpr,
        "split_rows": {
            "fit": int(fit_mask.sum()),
            "tuning": int(tune_mask.sum()),
            "calibration": int(cal_mask.sum()),
            "test": len(test),
        },
        "audit": {
            "train_duplicate_feature_rows": int(hashes.duplicated().sum()),
            "test_duplicate_feature_rows": int(test_hashes.duplicated().sum()),
            "test_rows_matching_training_features": int((~novel).sum()),
            "training_feature_groups_with_conflicting_labels": int(
                pd.DataFrame({"h": hashes, "y": train.label})
                .groupby("h")
                .y.nunique()
                .gt(1)
                .sum()
            ),
        },
        "dataset_files": {
            p.name: {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "rows": len(f),
            }
            for p, f in zip(paths, [train, test])
        },
        "baseline_tuning": baseline_tuning,
        "catboost_candidates": candidates,
        "validation": metrics(train.label[cal_mask], cp, threshold),
        "test": metrics(test.label, test_scores, threshold),
        "novel_test": metrics(test.label[novel], test_scores[novel], threshold),
        "per_attack_flag_rates": per_category,
        "category_classification": classification_report(
            test.attack_cat, cats, output_dict=True, zero_division=0
        ),
        "category_confusion_matrix": confusion_matrix(
            test.attack_cat, cats, labels=category.classes_
        ).tolist(),
        "category_classes": category.classes_.tolist(),
        "feature_importance": dict(
            sorted(
                zip(FEATURES, binary.feature_importances_.tolist()), key=lambda p: -p[1]
            )
        ),
        "training_seconds": round(time.time() - started, 2),
    }
    (reports / "evaluation.json").write_text(json.dumps(report, indent=2))
    output = test[["id", "proto", "service", "state", "attack_cat", "label"]].copy()
    output["attack_score"] = test_scores
    output["flagged"] = predictions.astype(bool)
    output["predicted_category"] = cats
    output.to_csv(reports / "test_predictions.csv", index=False)
    # Small held-out replay; real records, not fabricated dashboard metrics.
    sample = test.sample(n=300, random_state=SEED)
    (ROOT / "data/sample").mkdir(exist_ok=True)
    sample.to_csv(ROOT / "data/sample/heldout_labeled.csv", index=False)
    sample[FEATURES].to_csv(ROOT / "data/sample/flows.csv", index=False)
    md = [
        "# Held-out evaluation",
        "",
        f"Threshold: {threshold:.6f}; validation FPR budget: {args.max_fpr:.1%}.",
        "",
        "| Metric | Full official test | Test without train-feature duplicates |",
        "|---|---:|---:|",
    ]
    for key in [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "pr_auc_average_precision",
    ]:
        md.append(
            f'| {key} | {report["test"][key]:.4f} | {report["novel_test"][key]:.4f} |'
        )
    md += [
        "",
        f'Duplicate audit: `{json.dumps(report["audit"])}`.',
        "",
        "Confusion matrix (rows true normal/attack, columns predicted normal/attack):",
        "",
        f'```json\n{json.dumps(report["test"]["confusion_matrix"])}\n```',
        "",
        "These are supervised attack predictions on benchmark flow features, not proof of zero-day detection or live-network performance.",
        "The threshold is chosen on validation data; its false-positive budget is not guaranteed on shifted test or production traffic.",
        "Category suggestions use a separate model and may disagree with binary flags.",
        "",
        "Dataset: https://research.unsw.edu.au/projects/unsw-nb15-dataset",
        "Download mirror pinned at Mouwiya/UNSW-NB15-small revision 6f5f54594dfc80c84264aec4c7cc3d9b162f1e2f.",
        "Cite Moustafa and Slay (2015), UNSW-NB15: a comprehensive data set for network intrusion detection systems.",
    ]
    md += [
        "",
        "## Separate attack-category classification",
        "",
        "| Category | Precision | Recall | F1 | Test rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in report["category_classes"]:
        row = report["category_classification"][name]
        md.append(
            f'| {name} | {row["precision"]:.4f} | {row["recall"]:.4f} | {row["f1-score"]:.4f} | {int(row["support"])} |'
        )
    macro = report["category_classification"]["macro avg"]["f1-score"]
    md += [
        "",
        f"Multiclass macro-F1: {macro:.4f}. Category predictions are separate from the binary flag decision.",
    ]
    (reports / "evaluation.md").write_text("\n".join(md) + "\n")
    print(json.dumps(report["test"], indent=2), flush=True)
    print("Training completed in", report["training_seconds"], "seconds", flush=True)


if __name__ == "__main__":
    main()
