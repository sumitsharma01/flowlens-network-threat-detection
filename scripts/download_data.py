"""Fetch version-pinned UNSW-NB15 CSV mirrors; validate shape and record checksums."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://huggingface.co/datasets/Mouwiya/UNSW-NB15-small/resolve/6f5f54594dfc80c84264aec4c7cc3d9b162f1e2f/"

EXPECTED_HASHES = {
    "training": "bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa",
    "testing": "734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559",
}


def main():
    destination = ROOT / "data/raw"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for split, expected in [("training", 175341), ("testing", 82332)]:
        name = f"UNSW_NB15_{split}-set.csv"
        path = destination / name
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            with urlopen(BASE + name, timeout=120) as response, temporary.open(
                "wb"
            ) as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            temporary.replace(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != EXPECTED_HASHES[split]:
            raise ValueError(f"Checksum mismatch: {name}; remove it and download again")
        data = pd.read_csv(path)
        if len(data) != expected or not {"label", "attack_cat", "proto"}.issubset(
            data.columns
        ):
            raise ValueError(f"Unexpected dataset: {name}")
        manifest[name] = {
            "url": BASE + name,
            "rows": len(data),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        print(name, manifest[name])
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
