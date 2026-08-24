# W4H Compute METs (SQL)

YAML-bound **SQL** contribution: the **API** binds GeoMTS roles from `w4h.tables` and executes [`sql/compute.sql`](sql/compute.sql) in Postgres. This repo also ships a **notebook** and **CLI** that pick **one dataset in a project** (projects may have several) and call those APIs. They do not run SQL or the METs formula locally.

Distinct from the pandas companion [`w4h-compute-mets`](https://github.com/USC-InfoLab/w4h-compute-mets).

**Publisher:** usc-infolab · **Kinds:** sql, notebook, cli · **Language:** sql

**Not medical advice.** Research/demo estimate only.

## What the API does (generic)

METs is one job on this engine. The API does **not** hardcode the formula.

| Endpoint | Role |
| --- | --- |
| `GET /datasets/:id/signals` | Table metadata: mapped signals, physical `schema.table`, columns, `sampling_interval` |
| `POST /datasets/:id/contributions/:slug/sql` | Bind the contribution’s YAML SQL from `w4h.tables` and execute it (preview, or `write_back: true`) |

There is no `POST { sql: "..." }`. Identifiers come only from mapping + `information_schema`.

The notebook/CLI also use `GET /projects/:id` so you can list linked datasets and choose which one to run against.

## Formula (in `sql/compute.sql`, not in the API)

```
METs ≈ calories / (weight_kg × 0.25)   — per a 15-minute reference interval
```

The `0.25` constant is calibrated for **15 minutes** (classic 1 MET ≈ 1 kcal/kg/hour). The engine scales it to the signal’s native row interval from `w4h.tables.mapping_json.sampling_interval` (Fitbit `1min`, ICDE demo `5min`). Applying `0.25` unscaled to 1-minute rows is ~17× too low; defaulting ICDE to 1 minute is ~5× too high.

**Missing weight:** last known weight at or before each calories timestamp; else `70` kg and `weight_is_default = true`.

Output is a **new** mapped table (`{table_prefix}_mets_computed`, e.g. `icde_demo_mets_computed`). Source calories/weight tables are never mutated.

## Who should do what

| Role | What to do |
| --- | --- |
| **User** | List datasets, inspect signals, **preview** (no write). |
| **Admin** | Preview, then `--write-back` / `write_back: true` to materialize `mets_computed`. |
| **Super admin** | Catalog the row (`kinds: sql, notebook, cli`). |

## Prerequisites

- Running **w4h-api** with this slice of ADR-023 / D-34
- This repo checked out **next to** `w4h-api` (the API loads `manifest.yaml` + `sql/compute.sql` from the sibling folder)
- A **project** that may have **multiple datasets** — you always target one dataset
- That dataset has mapped `calories` and `weight` (ICDE demo `table_prefix: icde_demo`, 5 min, or Fitbit `fitbit`, 1 min)
- Personal API key (Profile → API keys). Not a read-only Samples sandbox dataset for write-back

```
W4H/
  w4h-api/
  w4h-sql-compute-mets/
  w4h-sample-icde-demo-csv/
```

## Notebook + CLI

```bash
cp .env.example .env   # W4H_API_KEY, W4H_PROJECT_ID, optional W4H_DATASET_ID
pip install -e .
```

List datasets in the project (required when the project has more than one):

```bash
w4h-sql-compute-mets datasets --project-id "$W4H_PROJECT_ID"
```

Table metadata for one dataset:

```bash
w4h-sql-compute-mets signals --project-id "$W4H_PROJECT_ID" --dataset-id "$W4H_DATASET_ID"
```

Preview METs (API runs the SQL):

```bash
w4h-sql-compute-mets compute --project-id "$W4H_PROJECT_ID" --dataset-id "$W4H_DATASET_ID"
# already-ingested data without sampling_interval on the mapping:
w4h-sql-compute-mets compute --project-id "$W4H_PROJECT_ID" --dataset-id "$W4H_DATASET_ID" --interval-minutes 5   # ICDE
w4h-sql-compute-mets compute --project-id "$W4H_PROJECT_ID" --dataset-id "$W4H_DATASET_ID" --interval-minutes 1   # Fitbit
```

Materialize (Team admin / project owner):

```bash
w4h-sql-compute-mets compute --project-id "$W4H_PROJECT_ID" --dataset-id "$W4H_DATASET_ID" --write-back
```

If you pass only `--project-id` and that project has **one** dataset, the CLI uses it. If it has **several**, it prints the list and asks for `--dataset-id`.

Or open [`notebook/compute_mets.ipynb`](notebook/compute_mets.ipynb) and run the cells (same client).

## curl (same APIs)

Discovery:

```bash
curl -sS -H "Authorization: Bearer $W4H_API_KEY" \
  "$W4H_API_BASE/datasets/$W4H_DATASET_ID/signals"
```

Preview:

```bash
curl -sS -X POST -H "Authorization: Bearer $W4H_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"interval_minutes": 5}' \
  "$W4H_API_BASE/datasets/$W4H_DATASET_ID/contributions/w4h-sql-compute-mets/sql"
```

Materialize:

```bash
curl -sS -X POST -H "Authorization: Bearer $W4H_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"write_back": true, "interval_minutes": 5}' \
  "$W4H_API_BASE/datasets/$W4H_DATASET_ID/contributions/w4h-sql-compute-mets/sql"
```

`interval_minutes` is optional when mapping already has `sampling_interval`. Re-ingest after the API started persisting interval so ICDE rows store `5min` automatically.

## Placeholders

Bound only from `w4h.tables` / `information_schema` (never client SQL):

| Placeholder | Meaning |
| --- | --- |
| `{{calories_rel}}` / `{{weight_rel}}` | `schema.table` |
| `{{calories_subject_col}}` / `{{weight_subject_col}}` | subject column |
| `{{calories_col}}` / `{{weight_col}}` | value column |
| `{{calories_ts_expr}}` / `{{weight_ts_expr}}` | timestamp expression (including `combine: [date, timestamp]`) |
| `{{calories_interval_minutes}}` | native calories row interval |
| `{{reference_interval_minutes}}` | formula reference (15) from the manifest |
| `{{default_weight_kg}}` | missing-weight fallback (70) |
