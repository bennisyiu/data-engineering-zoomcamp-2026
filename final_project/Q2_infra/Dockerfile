# Airflow image with Python deps for extract_load + dbt (Phase 5 local run)
FROM apache/airflow:2.7.3

USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
# Airflow 2.7 image uses Python 3.8; dbt-postgres 1.10+ needs 3.10+, so pin to 1.8.x
RUN pip install --no-cache-dir \
    pandas sqlalchemy psycopg2-binary python-dotenv \
    dbt-postgres==1.8.2
