#!/usr/bin/env bash
set -euo pipefail

role="${AIRFLOW_ROLE:-webserver}"

case "${role}" in
  webserver)
    airflow db migrate
    if [[ -n "${AIRFLOW_ADMIN_PASSWORD:-}" ]]; then
      airflow users create \
        --role Admin \
        --username "${AIRFLOW_ADMIN_USER:-admin}" \
        --email "${AIRFLOW_ADMIN_EMAIL:-admin@example.com}" \
        --firstname Portfolio \
        --lastname Admin \
        --password "${AIRFLOW_ADMIN_PASSWORD}" \
        || airflow users reset-password \
          --username "${AIRFLOW_ADMIN_USER:-admin}" \
          --password "${AIRFLOW_ADMIN_PASSWORD}"
    fi
    exec airflow webserver --port "${PORT:-8080}"
    ;;
  scheduler)
    airflow db migrate
    if [[ "${AIRFLOW_UNPAUSE_DAG:-true}" == "true" ]]; then
      airflow dags unpause insurance_elt_pipeline || true
    fi
    exec airflow scheduler
    ;;
  *)
    echo "AIRFLOW_ROLE must be webserver or scheduler" >&2
    exit 2
    ;;
esac
