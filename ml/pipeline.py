"""Reusable model-building stages for the training CLI and teaching notebook."""

from catboost import CatBoostClassifier
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from ml.features import FEATURES, CATEGORICAL


def baseline_pipeline(seed=42):
    """Fit encoders/scalers inside the pipeline, using fitting rows only."""
    numeric = [name for name in FEATURES if name not in CATEGORICAL]
    preprocessing = ColumnTransformer(
        [
            ("numeric", StandardScaler(), numeric),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return make_pipeline(
        preprocessing, LogisticRegression(max_iter=1000, random_state=seed)
    )


def binary_model(iterations=600, depth=8, attack_weight=1, seed=42, tuning=False):
    """Return an unfitted tree model; categorical fields remain strings.

    Scaling and one-hot encoding are not applied to CatBoost. AUC monitors
    candidate early stopping; candidate selection separately uses average
    precision. Refit models use the already-selected iteration count.
    """
    parameters = dict(
        iterations=iterations,
        depth=depth,
        learning_rate=0.08,
        l2_leaf_reg=5,
        loss_function="Logloss",
        class_weights=[1, attack_weight],
        random_seed=seed,
        thread_count=4,
        allow_writing_files=False,
        verbose=False,
    )
    if tuning:
        parameters["eval_metric"] = "AUC"
    return CatBoostClassifier(**parameters)


def category_model(iterations=600, seed=42, verbose=100):
    """Independent multiclass classifier, not the source of binary flag decisions."""
    return CatBoostClassifier(
        iterations=iterations,
        depth=8,
        learning_rate=0.08,
        loss_function="MultiClass",
        random_seed=seed,
        thread_count=4,
        allow_writing_files=False,
        verbose=verbose,
    )
