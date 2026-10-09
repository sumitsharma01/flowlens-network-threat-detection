"""Binary evaluation and operating-point selection, shared by CLI, API and notebook."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def metrics(y, scores, threshold):
    predictions = (np.asarray(scores) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    return {
        "rows": len(y),
        "accuracy": float(accuracy_score(y, predictions)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "pr_auc_average_precision": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "false_positive_rate": float(fp / (fp + tn)),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
    }


def choose_threshold(y, scores, max_fpr):
    fpr, tpr, thresholds = roc_curve(y, scores, drop_intermediate=False)
    eligible = np.where((fpr <= max_fpr) & np.isfinite(thresholds))[0]
    if not len(eligible):
        return float(np.nextafter(max(scores), np.inf))
    # Highest recall within false-alarm budget; favor lower FPR in ties.
    best = sorted(eligible, key=lambda i: (-tpr[i], fpr[i], -thresholds[i]))[0]
    return float(thresholds[best])
