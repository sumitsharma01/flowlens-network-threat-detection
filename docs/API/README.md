# Implemented API

Run the server and open `/docs` for the generated OpenAPI specification.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Loaded model health |
| GET | `/api/model-info` | Feature schema, threshold, version |
| GET | `/api/metrics` | Held-out evaluation report |
| POST | `/api/predict` | JSON `{"flows": [{...42 feature fields...}]}`; no persistence |
| POST | `/api/upload` | Multipart CSV field `file`; creates a review batch |
| POST | `/api/replay` | Score 300 real held-out sample records |
| GET | `/api/batches` | Latest 30 batch summaries |
| GET | `/api/batches/{id}` | Paginated flow results: offset, limit (1–500), flagged_only |
| GET | `/api/batches/{id}/export` | Export every prediction from a batch |
| POST | `/api/explain` | Explain up to 100 JSON flows using native TreeSHAP |
| GET | `/api/batches/{id}/flows/{row_number}/explain` | Explain a stored flow; 409 for missing features or stale model |
| GET | `/api/dataset-quality` | Measured quality audit of the pinned dataset |
| GET | `/api/sample` | Feature-only example CSV |

Invalid CSV/features produce 422; large uploads produce 413; absent batches produce 404.
`attack_score` is an uncalibrated model probability. `flagged` compares it with the stored validation-selected threshold. `category_suggestion` comes from a separate multiclass model and can disagree. All API responses use the stored model version; there is no runtime threshold override.

Local use only; authentication is not implemented.
