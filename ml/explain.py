"""Native TreeSHAP explanations for the binary detector's raw model score.

Feature contributions add in log-odds space, not probability space. They describe
model behavior and are not causal evidence or proof that a flow is malicious.
"""

import math
import numpy as np
from catboost import Pool
from ml.features import CATEGORICAL, FEATURES, prepare


def sigmoid(raw_score):
    """Convert a raw binary model score to probability without overflow."""
    if raw_score >= 0:
        return 1.0 / (1.0 + math.exp(-raw_score))
    exponential = math.exp(raw_score)
    return exponential / (1.0 + exponential)


def explain_flows(detector, frame, top_k=10):
    """Explain validated flows using the same loaded model as prediction.

    Keep the strongest absolute contributions and combine omitted terms into
    `other_contribution`, preserving the full raw-score reconstruction.
    """
    if not 1 <= top_k <= len(FEATURES):
        raise ValueError("top_k must be between 1 and the feature count")
    features = prepare(frame)
    pool = Pool(features, cat_features=CATEGORICAL)
    shap_values = detector.binary.get_feature_importance(
        pool, type="ShapValues", thread_count=4
    )
    raw_scores = detector.binary.predict(
        features, prediction_type="RawFormulaVal", thread_count=4
    )
    threshold = detector.metadata["threshold"]
    threshold_raw = math.log(threshold / (1 - threshold)) if 0 < threshold < 1 else None
    explanations = []
    for position, (terms, raw) in enumerate(zip(shap_values, raw_scores)):
        contributions, base = terms[:-1], float(terms[-1])
        ranked = np.argsort(-np.abs(contributions))[:top_k]
        top_features = []
        for index in ranked:
            feature = FEATURES[index]
            value = features.iloc[position][feature]
            contribution = float(contributions[index])
            top_features.append(
                {
                    "feature": feature,
                    "value": str(value) if feature in CATEGORICAL else float(value),
                    "contribution": contribution,
                    "direction": (
                        "toward attack"
                        if contribution > 0
                        else ("toward normal" if contribution < 0 else "neutral")
                    ),
                }
            )
        score = sigmoid(float(raw))
        explanations.append(
            {
                "model_version": detector.metadata["model_version"],
                "method": "CatBoost native TreeSHAP",
                "contribution_units": "log-odds",
                "attack_score": score,
                "threshold": threshold,
                "flagged": score >= threshold,
                "base_log_odds": base,
                "raw_log_odds": float(raw),
                "threshold_log_odds": threshold_raw,
                "top_features": top_features,
                "other_contribution": float(
                    contributions.sum() - contributions[ranked].sum()
                ),
                "reconstruction_error": float(base + contributions.sum() - raw),
            }
        )
    return explanations
