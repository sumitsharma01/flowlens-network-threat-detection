"""Load native CatBoost artifacts and score feature rows consistently."""

import argparse
import json
from pathlib import Path
import pandas as pd
from catboost import CatBoostClassifier
from ml.features import prepare

ROOT = Path(__file__).resolve().parents[1]


class Detector:
    def __init__(self, artifact_dir=None):
        folder = Path(artifact_dir or ROOT / "artifacts")
        self.metadata = json.loads((folder / "metadata.json").read_text())
        self.binary = CatBoostClassifier()
        self.binary.load_model(str(folder / "binary.cbm"))
        self.category = CatBoostClassifier()
        self.category.load_model(str(folder / "category.cbm"))

    def predict(self, frame):
        features = prepare(frame)
        scores = self.binary.predict_proba(features)[:, 1]
        classes = self.category.predict(features).ravel()
        return pd.DataFrame(
            {
                "row_number": range(1, len(frame) + 1),
                "protocol": features.proto.to_numpy(),
                "service": features.service.to_numpy(),
                "state": features.state.to_numpy(),
                "attack_score": scores,
                "flagged": scores >= self.metadata["threshold"],
                "predicted_label": [
                    "attack" if s >= self.metadata["threshold"] else "normal"
                    for s in scores
                ],
                "category_suggestion": classes,
                "model_version": self.metadata["model_version"],
            }
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = Detector().predict(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(
        f"Scored {len(result)} flows; flagged {int(result.flagged.sum())}. Saved {args.output}"
    )


if __name__ == "__main__":
    main()
