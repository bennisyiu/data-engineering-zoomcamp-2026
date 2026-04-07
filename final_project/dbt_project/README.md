# dbt project — Insurance DWH

This project has been created to build the medallion layers (staging → intermediate → marts) for the insurance data warehouse. With Postgres and `.env` configured, run from the repo root: `cd dbt_project`, then `dbt deps`, `dbt run`, `dbt test`. Profiles and model layout are documented in the project files.

Reviewer-facing URLs and credentials for Airflow, Postgres, Tableau, and Streamlit are in the parent [`README.md`](../README.md).
