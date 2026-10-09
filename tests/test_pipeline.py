import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from ml.features import FEATURES, prepare, fingerprints
from ml.train import choose_threshold, metrics
from ml.predict import ROOT, Detector


@pytest.fixture
def flow():
    frame = pd.DataFrame([{c: 0 for c in FEATURES}])
    frame["proto"] = "tcp"
    frame["service"] = "-"
    frame["state"] = "FIN"
    return frame


def test_targets_never_enter_features(flow):
    flow["label"] = 1
    flow["attack_cat"] = "Exploits"
    flow["id"] = 99
    assert list(prepare(flow).columns) == FEATURES
    h = fingerprints(flow).iloc[0]
    flow["label"] = 0
    flow["attack_cat"] = "Normal"
    flow["id"] = 1
    assert fingerprints(flow).iloc[0] == h


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, "oops"])
def test_invalid_numeric_rejected(flow, value):
    flow["dur"] = value
    with pytest.raises(ValueError):
        prepare(flow)


def test_missing_and_unknown_schema_rejected(flow):
    with pytest.raises(ValueError):
        prepare(flow.drop(columns=["dur"]))
    with pytest.raises(ValueError):
        prepare(flow.assign(unexpected=1))


def test_threshold_controls_validation_false_alarms():
    y = np.array([0, 0, 0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.3, 0.7, 0.6, 0.9])
    threshold = choose_threshold(y, scores, 0.0)
    m = metrics(y, scores, threshold)
    assert m["false_positive_rate"] == 0
    assert m["recall"] == 0.5


def test_threshold_ties_do_not_break_budget():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.2, 0.8, 0.8, 0.9])
    threshold = choose_threshold(y, scores, 0.1)
    assert metrics(y, scores, threshold)["false_positive_rate"] == 0


@pytest.fixture
def client(tmp_path, monkeypatch):
    if not (ROOT / "artifacts/binary.cbm").exists():
        pytest.skip("Train model to enable artifact integration tests")
    import backend.app as backend

    monkeypatch.setattr(backend, "DB", tmp_path / "test.sqlite3")
    with TestClient(backend.app) as client:
        yield client


def test_actual_model_ignores_truth_labels():
    if not (ROOT / "artifacts/binary.cbm").exists():
        pytest.skip("Train models first")
    sample = pd.read_csv(ROOT / "data/sample/heldout_labeled.csv").head(5)
    detector = Detector()
    expected = detector.predict(sample)
    sample["label"] = 1 - sample["label"]
    sample["attack_cat"] = "MadeUp"
    pd.testing.assert_frame_equal(expected, detector.predict(sample))


def test_api_replay_persistence_filter_and_export(client):
    response = client.post("/api/replay")
    assert response.status_code == 200
    batch = response.json()
    assert batch["summary"]["total_flows"] == 300
    assert len(batch["results"]) == 300
    saved = client.get(f'/api/batches/{batch["id"]}?flagged_only=true&limit=50').json()
    assert saved["matching_flows"] == batch["summary"]["flagged_flows"]
    assert all(r["flagged"] for r in saved["results"])
    assert client.get("/api/batches").json()[0]["id"] == batch["id"]
    exported = client.get(f'/api/batches/{batch["id"]}/export')
    assert len(pd.read_csv(io.StringIO(exported.text))) == 300
    assert client.get("/api/metrics").json()["test"]["rows"] == 82332


def test_upload_matches_cli_and_metadata_not_features(client):
    sample = pd.read_csv(ROOT / "data/sample/heldout_labeled.csv").head(3)
    expected = Detector().predict(sample).attack_score.tolist()
    response = client.post(
        "/api/upload",
        files={"file": ("flows.csv", sample.to_csv(index=False), "text/csv")},
    )
    assert response.status_code == 200
    assert [r["attack_score"] for r in response.json()["results"]] == expected
    bad = client.post(
        "/api/upload", files={"file": ("bad.csv", "proto\ntcp\n", "text/csv")}
    )
    assert bad.status_code == 422
    assert client.get("/api/batches/not-present").status_code == 404
    assert client.post("/api/predict", json={"flows": []}).status_code == 422
    assert client.get("/api/batches/not-present?limit=501").status_code == 422


def test_unknown_categories_and_json_predict(client):
    sample = pd.read_csv(ROOT / "data/sample/flows.csv").head(1)
    sample["proto"] = "unseen-protocol"
    response = client.post("/api/predict", json={"flows": sample.to_dict("records")})
    assert response.status_code == 200
    assert 0 <= response.json()["results"][0]["attack_score"] <= 1


def test_csv_formula_safety(client):
    sample = pd.read_csv(ROOT / "data/sample/flows.csv").head(1)
    sample["proto"] = "=1+1"
    response = client.post(
        "/api/upload",
        files={"file": ("flows.csv", sample.to_csv(index=False), "text/csv")},
    )
    assert response.status_code == 200
    exported = client.get(f'/api/batches/{response.json()["id"]}/export')
    assert pd.read_csv(io.StringIO(exported.text)).protocol.iloc[0] == "'=1+1"


def test_development_split_keeps_duplicate_feature_groups_together(flow):
    from ml.splits import development_split

    # Twenty unique flows, each repeated five times, balanced across binary labels.
    frame = pd.concat([flow] * 100, ignore_index=True)
    frame["dur"] = np.repeat(np.arange(20), 5)
    frame["label"] = np.repeat(np.arange(20) % 2, 5)
    masks, hashes = development_split(frame)
    assigned = masks[0].astype(int) + masks[1].astype(int) + masks[2].astype(int)
    assert assigned.eq(1).all()
    groups = [set(hashes[mask]) for mask in masks]
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])


def test_shap_reconstructs_score_and_matches_prediction():
    if not (ROOT / "artifacts/binary.cbm").exists():
        pytest.skip("Train models first")
    from ml.explain import explain_flows, sigmoid

    sample = pd.read_csv(ROOT / "data/sample/heldout_labeled.csv").head(3)
    detector = Detector()
    predictions = detector.predict(sample)
    explanations = explain_flows(detector, sample, top_k=5)
    for position, explanation in enumerate(explanations):
        reconstructed = (
            explanation["base_log_odds"]
            + sum(term["contribution"] for term in explanation["top_features"])
            + explanation["other_contribution"]
        )
        assert abs(reconstructed - explanation["raw_log_odds"]) < 1e-8
        assert abs(explanation["reconstruction_error"]) < 1e-8
        assert np.isclose(
            sigmoid(reconstructed), predictions.attack_score.iloc[position], atol=1e-12
        )
        assert explanation["flagged"] == bool(predictions.flagged.iloc[position])
        assert not {"label", "attack_cat", "id"}.intersection(
            t["feature"] for t in explanation["top_features"]
        )


def test_explain_api_stored_flow_and_quality(client):
    batch = client.post("/api/replay").json()
    explanation = client.get(f'/api/batches/{batch["id"]}/flows/2/explain')
    assert explanation.status_code == 200
    result = explanation.json()
    assert result["row_number"] == 2
    assert np.isclose(result["attack_score"], batch["results"][1]["attack_score"])
    assert abs(result["reconstruction_error"]) < 1e-8
    assert client.get(f'/api/batches/{batch["id"]}/flows/0/explain').status_code == 404
    quality = client.get("/api/dataset-quality").json()
    assert quality["splits"]["training"]["rows"] == 175341
    assert quality["splits"]["training"]["conflicting_binary_label_groups"] == 229
    sample = pd.read_csv(ROOT / "data/sample/flows.csv").head(1)
    assert (
        client.post(
            "/api/explain", json={"flows": sample.to_dict("records")}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/explain", json={"flows": sample.to_dict("records") * 101}
        ).status_code
        == 413
    )


def test_explanation_rejects_stale_model_version(client):
    import backend.app as backend

    batch = client.post("/api/replay").json()
    with backend.connect() as db:
        summary = batch["summary"] | {"model_version": "different-model"}
        db.execute(
            "UPDATE batches SET summary=? WHERE id=?",
            (json.dumps(summary), batch["id"]),
        )
    assert client.get(f'/api/batches/{batch["id"]}/flows/1/explain').status_code == 409


def test_legacy_database_migrates_without_inventing_explanations(tmp_path, monkeypatch):
    if not (ROOT / "artifacts/binary.cbm").exists():
        pytest.skip("Train models first")
    import backend.app as backend

    monkeypatch.setattr(backend, "DB", tmp_path / "legacy.sqlite3")
    with backend.connect() as db:
        db.execute(
            "CREATE TABLE batches (id TEXT PRIMARY KEY, created_at TEXT, source TEXT, summary TEXT, results TEXT)"
        )
        db.execute(
            "INSERT INTO batches VALUES (?,?,?,?,?)",
            ("legacy", "2026-01-01", "old", "{}", "[]"),
        )
    with TestClient(backend.app) as session:
        response = session.get("/api/batches/legacy/flows/1/explain")
        assert response.status_code == 409
        assert "Replay or upload" in response.json()["detail"]
    with backend.connect() as db:
        assert "features" in {
            row["name"] for row in db.execute("PRAGMA table_info(batches)")
        }
