# AGENTS.md — w4h-sql-compute-mets

YAML-bound SQL contribution that derives `mets_computed` from calories + weight (ADR-023). Not the pandas `w4h-compute-mets` repo.

- Formula lives in `sql/compute.sql` + `manifest.yaml`. The API only binds identifiers from `w4h.tables`. Do not hardcode `fitbit_*` or `icde_demo_*` table names and do not port the formula into `w4h-api/lib`.
- Notebook + CLI (`w4h_sql_compute_mets`) are thin HTTP clients: `GET /projects/:id` (list datasets), `GET /datasets/:id/signals` (table metadata), `POST /datasets/:id/contributions/:slug/sql` (bind/execute). They must not compute METs in Python or open a Postgres URL.
- Always target **one dataset**. A project may have several — require `--dataset-id` (or env `W4H_DATASET_ID`) when more than one is linked. Never assume the first dataset.
- Bindings are GeoMTS roles resolved by **w4h-api**. Do not add a free-SQL client (`POST { sql }`) or direct Postgres credentials.
- API key via `W4H_API_KEY` in local `.env` only — never in git.
- Interval comes from mapping `sampling_interval` (1 min Fitbit, 5 min ICDE). Do not guess from table names. Already-ingested data may pass `--interval-minutes`.
- New data → new table (`{prefix}_mets_computed`). Never update calories/weight in place.
