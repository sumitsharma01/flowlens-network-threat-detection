"""Render actual held-out evaluation as a standalone chart."""

import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = json.loads((ROOT / "reports/evaluation.json").read_text())
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    cm = np.asarray(report["test"]["confusion_matrix"])
    axes[0].imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            axes[0].text(
                j,
                i,
                f"{cm[i,j]:,}",
                ha="center",
                va="center",
                fontsize=22,
                color="white" if cm[i, j] > cm.max() / 2 else "#173453",
            )
    axes[0].set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Normal", "Attack"],
        yticklabels=["Normal", "Attack"],
        xlabel="Predicted class",
        ylabel="Actual class",
        title="Binary detector · confusion matrix",
    )
    rates = {k: v for k, v in report["per_attack_flag_rates"].items() if k != "Normal"}
    labels = list(rates)
    values = [100 * rates[k]["flag_rate"] for k in labels]
    axes[1].barh(labels, values, color="#167fba")
    axes[1].invert_yaxis()
    axes[1].set(
        xlim=(0, 110),
        xlabel="Attack flows flagged (%)",
        title="Detection recall by true attack category",
    )
    for i, value in enumerate(values):
        axes[1].text(value + 1, i, f"{value:.1f}%", va="center", fontsize=10)
    axes[1].spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        f'UNSW-NB15 · {report["test"]["rows"]:,} held-out flows | F1 {report["test"]["f1"]:.3f} | False-positive rate {report["test"]["false_positive_rate"]:.1%}',
        fontsize=15,
        fontweight="bold",
    )
    fig.savefig(ROOT / "reports/evaluation.png", dpi=170)


if __name__ == "__main__":
    main()
