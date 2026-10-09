# Local review database

SQLite file `data/monitor.sqlite3`, overridable with `MONITOR_DB`.

`batches`: id (UUID text primary key), created_at (UTC ISO text), source (text), summary (JSON text), results (JSON text), features (JSON text, nullable for legacy batches).

Each batch stores model version, decision threshold, total/flagged counts, row-order chart aggregates, and all per-flow predictions. Labels, if supplied, are retained for review only. Validated 42-feature vectors are persisted for per-flow explanations; original uploaded CSV files are not retained. Legacy batches without features require replay/upload again. Pagination filters stored prediction records; export includes the complete batch.

This is an MVP schema for one local reviewer, not a multi-tenant production incident database.
