"""Development splits based on feature groups, rather than individual rows."""

import pandas as pd
from sklearn.model_selection import train_test_split
from ml.features import fingerprints


def development_split(frame, seed=42):
    """Return fit/tune/calibration masks without sharing exact feature duplicates.

    The nominal 60/20/20 proportions apply to unique feature groups. Row counts
    differ because groups contain different numbers of duplicate records.
    For stratification only, a conflicting-label group is assigned its maximum
    binary label. Actual row labels remain unchanged for training/evaluation.
    No test records or test labels are used to construct these masks.
    """
    hashes = fingerprints(frame)
    groups = (
        pd.DataFrame({"hash": hashes, "label": frame.label}).groupby("hash").label.max()
    )
    development, calibration = train_test_split(
        groups.index, test_size=0.2, random_state=seed, stratify=groups
    )
    fitting, tuning = train_test_split(
        development, test_size=0.25, random_state=seed, stratify=groups.loc[development]
    )
    masks = tuple(hashes.isin(group) for group in (fitting, tuning, calibration))
    return masks, hashes
