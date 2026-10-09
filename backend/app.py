"""Local flow-review API and dashboard. No packet capture is implied."""

import csv
import io
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from ml.features import FEATURES, prepare
from ml.explain import explain_flows
from ml.predict import Detector, ROOT

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20000
DB = Path(os.getenv("MONITOR_DB", str(ROOT / "data/monitor.sqlite3")))


@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app):
    app.state.detector = Detector()
    with connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, created_at TEXT, source TEXT, summary TEXT, results TEXT, features TEXT)"
        )
        # Upgrade review databases created before per-flow explainability existed.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(batches)")}
        if "features" not in columns:
            db.execute("ALTER TABLE batches ADD COLUMN features TEXT")
    yield


app = FastAPI(title="Cloud AI Network Monitor", version="1.0.0", lifespan=lifespan)


class PredictionRequest(BaseModel):
    flows: list[dict] = Field(min_length=1, max_length=1000)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_version": app.state.detector.metadata["model_version"],
    }


@app.get("/api/model-info")
def info():
    return app.state.detector.metadata


@app.get("/api/metrics")
def evaluation():
    return json.loads((ROOT / "reports/evaluation.json").read_text())


@app.post("/api/predict")
def predict(request: PredictionRequest):
    try:
        return {
            "results": app.state.detector.predict(pd.DataFrame(request.flows)).to_dict(
                "records"
            )
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def analyze(frame, source):
    if len(frame) > MAX_ROWS:
        raise HTTPException(
            413,
            f"Maximum {MAX_ROWS} flows per dashboard batch; use the CLI for larger files",
        )
    try:
        result = app.state.detector.predict(frame)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    records = result.to_dict("records")
    flag_counts = (
        result.loc[result.flagged, "category_suggestion"].value_counts().to_dict()
    )
    timeline = []
    for indexes in np.array_split(np.arange(len(result)), min(30, len(result))):
        rows = result.iloc[indexes]
        timeline.append(
            {
                "start_row": int(indexes[0]) + 1,
                "flows": len(rows),
                "flagged": int(rows.flagged.sum()),
            }
        )
    summary = {
        "total_flows": len(result),
        "flagged_flows": int(result.flagged.sum()),
        "normal_flows": int((~result.flagged).sum()),
        "flag_rate": float(result.flagged.mean()),
        "threshold": app.state.detector.metadata["threshold"],
        "category_counts": flag_counts,
        "timeline": timeline,
        "model_version": app.state.detector.metadata["model_version"],
    }
    if "label" in frame:
        labels = pd.to_numeric(frame.label, errors="coerce")
        if labels.isna().any() or not labels.isin([0, 1]).all():
            raise HTTPException(422, "Optional label column must contain only 0 or 1")
        from ml.evaluate import metrics

        if labels.nunique() == 2:
            summary["evaluation"] = metrics(
                labels, result.attack_score, summary["threshold"]
            )
        for record, label in zip(records, labels):
            record["actual_label"] = int(label)
    batch_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute(
            "INSERT INTO batches (id,created_at,source,summary,results,features) VALUES (?,?,?,?,?,?)",
            (
                batch_id,
                created,
                source,
                json.dumps(summary),
                json.dumps(records),
                json.dumps(prepare(frame).to_dict("records")),
            ),
        )
    return {
        "id": batch_id,
        "created_at": created,
        "source": source,
        "summary": summary,
        "results": records[:500],
    }


@app.post("/api/upload")
def upload(file: UploadFile):
    contents = file.file.read(MAX_BYTES + 1)
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, "CSV exceeds 10 MiB; use the CLI for larger files")
    try:
        frame = pd.read_csv(io.BytesIO(contents))
    except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise HTTPException(422, "Unable to parse UTF-8 CSV") from exc
    return analyze(frame, "Uploaded flow features")


@app.post("/api/replay")
def replay():
    return analyze(
        pd.read_csv(ROOT / "data/sample/heldout_labeled.csv"),
        "Held-out benchmark sample",
    )


@app.get("/api/batches")
def batches():
    with connect() as db:
        rows = db.execute(
            "SELECT id,created_at,source,summary FROM batches ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
    return [dict(r) | {"summary": json.loads(r["summary"])} for r in rows]


@app.get("/api/batches/{batch_id}")
def batch(batch_id: str, offset: int = 0, limit: int = 500, flagged_only: bool = False):
    if offset < 0 or not 1 <= limit <= 500:
        raise HTTPException(422, "Invalid pagination")
    with connect() as db:
        row = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Batch not found")
    records = json.loads(row["results"])
    if flagged_only:
        records = [r for r in records if r["flagged"]]
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "source": row["source"],
        "summary": json.loads(row["summary"]),
        "matching_flows": len(records),
        "results": records[offset : offset + limit],
    }


@app.get("/api/batches/{batch_id}/export")
def export(batch_id: str):
    with connect() as db:
        row = db.execute(
            "SELECT results FROM batches WHERE id=?", (batch_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Batch not found")
    records = json.loads(row["results"])
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(records[0]))
    writer.writeheader()
    for record in records:
        # Protect spreadsheet readers from formula injection in uploaded categories.
        writer.writerow(
            {
                k: (
                    "'" + v
                    if isinstance(v, str)
                    and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                )
                for k, v in record.items()
            }
        )
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="flow-predictions.csv"'},
    )


@app.get("/api/dataset-quality")
def dataset_quality():
    return json.loads((ROOT / "reports/dataset_quality.json").read_text())


@app.post("/api/explain")
def explain(request: PredictionRequest):
    if len(request.flows) > 100:
        raise HTTPException(413, "Explain at most 100 flows per request")
    try:
        return {
            "explanations": explain_flows(
                app.state.detector, pd.DataFrame(request.flows)
            )
        }
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/batches/{batch_id}/flows/{row_number}/explain")
def explain_batch_flow(batch_id: str, row_number: int):
    with connect() as db:
        row = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Batch not found")
    if row["features"] is None:
        raise HTTPException(
            409,
            "This older batch has no saved features. Replay or upload it again to enable explanations.",
        )
    summary = json.loads(row["summary"])
    if summary["model_version"] != app.state.detector.metadata["model_version"]:
        raise HTTPException(
            409,
            "This batch used a different model version. Re-score it before explaining.",
        )
    features = json.loads(row["features"])
    if not 1 <= row_number <= len(features):
        raise HTTPException(404, "Flow not found")
    result = explain_flows(
        app.state.detector, pd.DataFrame([features[row_number - 1]])
    )[0]
    result["row_number"] = row_number
    record = json.loads(row["results"])[row_number - 1]
    if "actual_label" in record:
        result["actual_label"] = record["actual_label"]
    return result


@app.get("/api/sample")
def sample():
    return FileResponse(
        ROOT / "data/sample/flows.csv",
        media_type="text/csv",
        filename="sample-flows.csv",
    )


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/")
def dashboard():
    return FileResponse(ROOT / "frontend/index.html")
