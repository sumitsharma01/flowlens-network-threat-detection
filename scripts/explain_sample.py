"""Save reproducible local and sample-level explanations from held-out flows."""

import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from catboost import Pool
from ml.features import FEATURES, CATEGORICAL, prepare
from ml.predict import Detector, ROOT
from ml.explain import explain_flows


def main():
    detector = Detector()
    sample = pd.read_csv(ROOT / "data/sample/heldout_labeled.csv")
    predictions = detector.predict(sample)
    # Explain a known false positive, making clear that attribution does not prove an attack.
    matches = np.flatnonzero(
        predictions.flagged.to_numpy() & sample.label.eq(0).to_numpy()
    )
    position = int(matches[0]) if len(matches) else 0
    explanation = explain_flows(detector, sample.iloc[[position]], top_k=42)[0]
    explanation["sample_row_number"] = position + 1
    explanation["actual_label"] = int(sample.label.iloc[position])
    (ROOT / "reports/example_explanation.json").write_text(
        json.dumps(explanation, indent=2)
    )
    top = explanation["top_features"][:10][::-1]
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.barh(
        [f["feature"] for f in top],
        [f["contribution"] for f in top],
        color=["#da6476" if f["contribution"] > 0 else "#168cb8" for f in top],
    )
    ax.axvline(0, color="gray", linewidth=1)
    ax.set(
        xlabel="Signed contribution to attack log-odds",
        title=f"Sample flow {position+1}: model explanation (actual label: normal)",
    )
    fig.savefig(ROOT / "reports/local_shap.png", dpi=160)
    plt.close(fig)
    # This is a deliberately bounded diagnostic sample, not population importance.
    features = prepare(sample.head(50))
    terms = detector.binary.get_feature_importance(
        Pool(features, cat_features=CATEGORICAL), type="ShapValues", thread_count=4
    )
    importance = pd.Series(
        np.abs(terms[:, :-1]).mean(axis=0), index=FEATURES
    ).sort_values()
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    importance.tail(12).plot.barh(ax=ax, color="#168cb8")
    ax.set(
        title="Mean absolute SHAP on 50 held-out sample flows",
        xlabel="Mean absolute contribution (log-odds)",
    )
    fig.savefig(ROOT / "reports/sample_shap.png", dpi=160)
    plt.close(fig)
    print("Saved explanation JSON and local/sample SHAP charts.")


if __name__ == "__main__":
    main()
