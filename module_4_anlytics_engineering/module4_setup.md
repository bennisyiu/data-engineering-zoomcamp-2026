# BigQuery Setup Guide (Module 4)

This is a BigQuery-first version of the Module 4 setup, adapted from the instructor's local DuckDB setup guide.

Reference used:
- https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/04-analytics-engineering/setup/local_setup.md

## Goal

Set up `dbt Core + BigQuery` so you can:

1. Ingest NYC taxi data into BigQuery (under your `zoomcamp` dataset)
2. Build dbt models from BigQuery sources
3. Run tests and answer homework questions

---

## 1) Create and activate Python environment

From `module_4_anlytics_engineering`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Quick checks:

```powershell
python -c "import requests, google.cloud.bigquery; print('ok')"
dbt --version
```

---

## 2) Configure BigQuery authentication

Use your service account JSON key.

Set for current terminal session:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account-key.json"
```

Set permanently for your Windows user:

```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\service-account-key.json"
```

Verify:

```powershell
Test-Path "$env:GOOGLE_APPLICATION_CREDENTIALS"
python -c "from google.cloud import bigquery; c=bigquery.Client(); print(c.project)"
```

---

## 3) Ingest raw taxi data into BigQuery

Your `ingest.py` already supports dataset selection with `--dataset`.

To load all data into the `zoomcamp` dataset:

```powershell
python ingest.py --project-id inlaid-rig-385510 --dataset zoomcamp --start-year 2019 --end-year 2020 --replace-tables
```

Expected destination tables:

- `inlaid-rig-385510.zoomcamp.yellow_tripdata`
- `inlaid-rig-385510.zoomcamp.green_tripdata`

Notes:
- `--replace-tables` drops and recreates destination tables.
- Remove it if you want append behavior.

---

## 4) Initialize dbt project (if starting from scratch)

From `module_4_anlytics_engineering`:

```powershell
dbt init taxi_rides_ny
```

Then run dbt commands from inside:

```powershell
cd .\taxi_rides_ny\
```

---

## 5) Configure `~/.dbt/profiles.yml` for BigQuery (recommended)

Yes, you should use the BigQuery version of `profiles.yml` (not DuckDB).

Windows location:
- `%USERPROFILE%\.dbt\profiles.yml`

Suggested profile:

```yaml
taxi_rides_ny:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: inlaid-rig-385510
      dataset: dbt_bennis_dev
      keyfile: C:/Users/Bennis/OneDrive - 10life/code/service-account-key.json
      location: US
      threads: 4
      timeout_seconds: 300
      priority: interactive
```

Important:
- `dataset` above is the dbt output dataset (where dbt writes models), not your raw source dataset.
- Keep raw source tables in `zoomcamp`.
- Use forward slashes in `keyfile` path for YAML portability.

---

## 6) Point dbt sources to `zoomcamp`

In your dbt project, your `sources.yml` should reference:

- database/project: `inlaid-rig-385510`
- schema/dataset: `zoomcamp`
- tables: `yellow_tripdata`, `green_tripdata` (and `fhv_tripdata` if needed)

If your project uses vars, run with:

```powershell
dbt run --vars "{'raw_dataset': 'zoomcamp'}"
```

---

## 7) Validate setup and run dbt

From `taxi_rides_ny`:

```powershell
dbt debug
dbt run
dbt test
```

If `dbt debug` passes and models build, your environment is ready for homework queries.

---

## 8) Homework readiness checklist

Before solving questions, confirm:

- Raw data exists in `inlaid-rig-385510.zoomcamp.*`
- dbt profile uses `type: bigquery`
- dbt models completed successfully (`dbt run`)
- tests are green or expected failures are understood (`dbt test`)

Then query your built models in BigQuery for:

- row counts
- zone-level revenue
- filtered trip counts

---

## Common pitfalls

- `DefaultCredentialsError`: credentials env var not visible in current terminal
- wrong dataset: forgot `--dataset zoomcamp` in `ingest.py` command
- wrong profile: `profiles.yml` still set to `duckdb`
- path issues: service account path contains backslashes in YAML

