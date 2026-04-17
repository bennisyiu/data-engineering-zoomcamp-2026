"""
Q2: Insurance ELT pipeline DAG.
Daily run: extract_load (CSV from data/ or S3 → raw schema), then dbt run and dbt test.
Expects: project mounted at /opt/airflow/repo; Postgres service `warehouse` (Compose network).
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

REPO = "/opt/airflow/repo"
DBT_PROJECT = os.path.join(REPO, "dbt_project")
# Writable paths: mounted repo is often root-owned; airflow user cannot write profiles.yml,
# dbt_packages/, target/, logs/, or package-lock.yml under dbt_project.
PROFILES_DIR = "/tmp"
DBT_WORK = "/tmp/dbt_insurance_elt_work"

with DAG(
    dag_id="insurance_elt_pipeline",
    default_args={
        "owner": "airflow",
        "retries": 1,
    },
    description="Daily load: CSVs (local or S3) → raw, then dbt transform and test",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    tags=["q2", "elt", "insurance"],
) as dag:

    # Inside Compose, DWH is always service `warehouse` on 5432. Shell `export` is reliable even when
    # Airflow's env merge or a mounted .env would otherwise leave POSTGRES_HOST=localhost.
    _pg_export = "export POSTGRES_HOST=warehouse POSTGRES_PORT=5432 && "

    _pg_dwh = {**os.environ, "POSTGRES_HOST": "warehouse", "POSTGRES_PORT": "5432"}

    load_raw = BashOperator(
        task_id="extract_load_csv_to_raw",
        bash_command=f"{_pg_export}cd {REPO} && python scripts/extract_load.py",
        env=_pg_dwh,
    )

    _env = {**_pg_dwh}

    _dbt_prepare = (
        f"set -e && cp {DBT_PROJECT}/profiles.yml.example {PROFILES_DIR}/profiles.yml && "
        f"rm -rf {DBT_WORK} && mkdir -p {DBT_WORK} && cp -a {DBT_PROJECT}/. {DBT_WORK}/"
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{_pg_export}{_dbt_prepare} && cd {DBT_WORK} && dbt deps && dbt run --profiles-dir {PROFILES_DIR}",
        env=_env,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{_pg_export}set -e && cp {DBT_PROJECT}/profiles.yml.example {PROFILES_DIR}/profiles.yml && "
            f"cd {DBT_WORK} && dbt test --profiles-dir {PROFILES_DIR}"
        ),
        env=_env,
    )

    load_raw >> dbt_run >> dbt_test
