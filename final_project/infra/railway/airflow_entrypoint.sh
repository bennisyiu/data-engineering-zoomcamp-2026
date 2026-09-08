#!/usr/bin/env bash
set -euo pipefail

if [[ "${DEMO_MODE:-false}" != "true" ]]; then
  echo "Airflow demo service is dormant. Set DEMO_MODE=true and redeploy to start it."
  exit 0
fi

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
    if [[ -n "${AIRFLOW_VIEWER_PASSWORD:-}" ]]; then
      airflow users create \
        --role Viewer \
        --username "${AIRFLOW_VIEWER_USER:-reviewer}" \
        --email "${AIRFLOW_VIEWER_EMAIL:-reviewer@example.com}" \
        --firstname Portfolio \
        --lastname Reviewer \
        --password "${AIRFLOW_VIEWER_PASSWORD}" \
        || airflow users reset-password \
          --username "${AIRFLOW_VIEWER_USER:-reviewer}" \
          --password "${AIRFLOW_VIEWER_PASSWORD}"
    fi
    exec airflow webserver --port "${PORT:-8080}"
    ;;
  scheduler)
    airflow db migrate
    if [[ "${AIRFLOW_UNPAUSE_DAG:-true}" == "true" ]]; then
      (
        for _ in {1..30}; do
          if airflow dags list 2>/dev/null | grep -q "insurance_elt_pipeline"; then
            airflow dags unpause insurance_elt_pipeline || true
            exit 0
          fi
          sleep 2
        done
        echo "DAG was not available to unpause during the startup window." >&2
      ) &
    fi
    exec airflow scheduler
    ;;
  *)
    echo "AIRFLOW_ROLE must be webserver or scheduler" >&2
    exit 2
    ;;
esac
