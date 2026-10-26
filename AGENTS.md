# AGENTS.md — w4h-sql-compute-mets

YAML-bound SQL contribution that derives `mets_computed` from calories + weight (ADR-023). Not the pandas `w4h-compute-mets` repo. The shared W4H architecture overview is at the end of this file.

## Where this repo fits in W4H

- **Layer:** contribution, kinds `sql` + `notebook` + `cli`, catalog slug `w4h-sql-compute-mets`, **`runnable = true`**. It is the first and reference `kind: sql` package (ADR-023).
- **It is executed by `w4h-api`, not by itself.** `lib/sql-contribution-engine.js` reads this repo's `manifest.yaml` and `sql/compute.sql` from the **sibling checkout** `../w4h-sql-compute-mets` at run time. If this folder is not next to `w4h-api`, the job fails. Edits to `compute.sql` take effect on the next run.
- **Two ways it is triggered, one engine:**
  - App: Analytics → **Run analysis...** → `POST /contributions/w4h-sql-compute-mets/run` (tracked in `w4h.contribution_runs`).
  - Notebook/CLI here: `GET /projects/:id` → `GET /datasets/:id/signals` → `POST /datasets/:id/contributions/w4h-sql-compute-mets/sql`.
- **Inputs:** mapped `calories` and `weight` tables created by ingest (`fitbit_*` from the Fitbit importers at `1min`, or `icde_demo_*` at `5min`). The engine binds `{{calories_rel}}`, `{{calories_col}}`, `{{calories_ts_expr}}`, … from `w4h.tables` and scales the formula by `sampling_interval`.
- **Output:** a **new** mapped table `<table_prefix>_mets_computed` (`id`, `ts`, `mets`, `weight_kg`, `weight_is_default`), registered in `w4h.tables`. In-app runs also refresh the dataset's cached summary afterwards.
- **Template for future SQL jobs:** roles in `requires` / `produces`, scalars in `scalars`, `run.materialize`, and only bound placeholders in SQL.

## Rules

- Formula lives in `sql/compute.sql` + `manifest.yaml`. The API only binds identifiers from `w4h.tables`. Do not hardcode `fitbit_*` or `icde_demo_*` table names and do not port the formula into `w4h-api/lib`.
- Notebook + CLI (`w4h_sql_compute_mets`) are thin HTTP clients: `GET /projects/:id` (list datasets), `GET /datasets/:id/signals` (table metadata), `POST /datasets/:id/contributions/:slug/sql` (bind/execute). They must not compute METs in Python or open a Postgres URL.
- Always target **one dataset**. A project may have several — require `--dataset-id` (or env `W4H_DATASET_ID`) when more than one is linked. Never assume the first dataset.
- Bindings are GeoMTS roles resolved by **w4h-api**. Do not add a free-SQL client (`POST { sql }`) or direct Postgres credentials.
- API key via `W4H_API_KEY` in local `.env` only — never in git.
- Interval comes from mapping `sampling_interval` (1 min Fitbit, 5 min ICDE). Do not guess from table names. Already-ingested data may pass `--interval-minutes`.
- New data → new table (`{prefix}_mets_computed`). Never update calories/weight in place.

<!-- BEGIN w4h-system-overview: identical in every W4H repo's AGENTS.md. Edit all copies together. -->

## W4H system overview (shared across all repos)

**W4H (Wearables for Health) Toolkit** loads wearable-device data into PostgreSQL, organizes it by team, project and dataset, controls access, and runs curated analyses on it. Each signal is a **GeoMTS** (Geospatial Multivariate Time Series) table whose roles (`subject`, `time`, optional `geo`, `values[]`) are stored in `w4h.tables.mapping_json`, not in fixed column names. Three repos form the platform, one packages it, and the rest are **contributions** listed in the in-app catalog (`w4h.contributions`).

| Repo | Role |
|---|---|
| `w4h-api` | Express API and Postgres DDL (`w4h` schema): auth, ACL, ingest, catalog, contribution runner, SQL engine. Port 2026 |
| `w4h-app` | Vue 3 + Vite SPA; talks only to `w4h-api`. Port 5173 |
| `w4h-docs` | Product rules, MVP, ADRs and guides; imported by the API as in-app Help. Owns product decisions |
| `w4h-docker` | Compose stack (`api`, `app`, `notebooks`) built from sibling repos; Postgres is external |
| `w4h-sample-fitbit-csv`, `w4h-sample-icde-demo-csv` | Synthetic sample CSVs plus `manifest.yaml` (ICDE includes a `gps_track` geo signal) |
| `w4h-sample-fitbit-csv-importer`, `w4h-sample-icde-demo-csv-importer` | Runnable importers (notebook, CLI, `run.sh`) for those samples |
| `w4h-fitbit-csv-file-importer` | Runnable importer for user-supplied Fitbit CSVs: profile headers, review a drafted mapping, ingest |
| `w4h-sql-compute-mets` | SQL contribution (YAML + SQL template) that `w4h-api` executes in-process |
| `fft_approximate` | Postgres C extension, catalog slug `fft-approximate`; no API involvement |
| `w4h-demo-approximate-queries` | Notebook comparing `fft_approximate` with exact averages over direct Postgres |

**Main flows:**

1. **Ingest:** importers post 500-row chunks to `POST /datasets/:id/import/csv-batch`. `lib/ingest-csv.js` creates `ds_<dataset_id>.<table_prefix>_<signal>` and upserts its `w4h.tables` mapping.
2. **In-app Run (ADR-022):** `POST /contributions/:slug/run` makes `lib/contribution-runner.js` spawn `../<slug>/run.sh` with the user's `W4H_API_KEY`, `W4H_API_BASE` and `W4H_DATASET_ID`. Stdout lines `@@PROGRESS@@ {json}` drive the progress bar.
3. **SQL analytics (ADR-023):** `lib/sql-contribution-engine.js` reads `../<slug>/manifest.yaml` and `sql/`, binds identifiers from `w4h.tables`, and runs in-process. There is no free-SQL endpoint.
4. **Extensions:** the operator installs `fft_approximate` on their Postgres; notebooks call it directly.

**Layout:** clone every repo as a sibling in one folder. The API finds contributions at `../<slug>` (override `CONTRIBUTION_RUNNER_REPO_ROOT`) and docs at `DOCS_REPO_PATH=../w4h-docs`.

**Cross-repo changes:** `w4h-api` first (regenerate `API_INDEX.md`), then `w4h-app`, then `w4h-docs`. Catalog rows are seeded in `w4h-api/data/schema.sql`. Start at `w4h-docs/dev/mvp.md` and `w4h-docs/dev/ADR-README.md` for decisions, and `w4h-docs/dev/developer-setup.md` for local setup, getting an API key, test personas, troubleshooting, per-repo test commands, default branches and a glossary. Do not commit or push unless asked; never commit `.env` files, API keys or participant data.

<!-- END w4h-system-overview -->
