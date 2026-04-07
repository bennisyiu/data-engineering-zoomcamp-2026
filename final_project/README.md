# Insurance Policy Analytics — DE Zoomcamp Course Project

> An end-to-end ELT pipeline that ingests insurance policy, invoice, and claim data into a cloud-hosted data warehouse and powers an interactive Tableau dashboard.

---

## Problem Statement

An insurance company generates transactional data across three domains — **policies**, **invoices**, and **claims** — but has no unified analytical layer. Business questions such as _"How does premium revenue compare between new and returning customers?"_ or _"Which products have the highest loss ratio?"_ require manual joining across raw tables with inconsistent types and no quality checks.

This project solves that by building a **full ELT pipeline**: raw CSVs are extracted and loaded into a PostgreSQL data warehouse via Python, transformed through a medallion architecture (raw → staging → intermediate → marts) using **dbt**, orchestrated end-to-end by **Apache Airflow**, and deployed on **AWS EC2 + S3**. The result is a set of clean, tested analytical tables that feed a **Tableau dashboard** with key insurance KPIs — no manual data wrangling required.

---

## Access for Reviewers

| What                    | Where                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code, SQL, dbt models   | This repo                                                                                                                                                                                       |
| Setup and Tableau notes | [`notes/`](notes/) (setup_guide.md, tableau_summary.md)                                                                                                                                         |
| Airflow UI (on EC2)     | `http://52.221.114.40:8082` — `admin` / `admin` (see [`infra/INFRA.md`](infra/INFRA.md))                                                                                                        |
| Database (PostgreSQL)   | `52.221.114.40:5432` / `insurance_dwh` — read-only credentials shared via email (see below)                                                                                                     |
| Tableau dashboard       | [Insurance Policy, Claims & Invoice Analytics](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link) (4 dashboards as a Story)                                   |
| Architecture diagrams   | [High-Level](docs/High-Level%20Architecture_drawio_image.png), [ELT Pipeline](<docs/ELT Pipeline (Airflow DAG)_drawio_image.png>), [Data Lineage](docs/Data%20Model%20Lineage_drawio_image.png) |
| Docker & cloud          | [`infra/INFRA.md`](infra/INFRA.md). **EC2:** use ≥30 GB root volume (default 8 GB fills and breaks the pipeline).                                                                               |

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Access for Reviewers](#access-for-reviewers)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Sources](#data-sources)
- [Exploratory Data Analysis](#exploratory-data-analysis)
- [Data Ingestion & Orchestration](#data-ingestion--orchestration)
- [Data Warehouse & Data Model](#data-warehouse--data-model)
- [Transformations (dbt)](#transformations-dbt)
- [Dashboard](#dashboard)
- [Cloud Infrastructure](#cloud-infrastructure)
- [Reproducibility / Getting Started](#reproducibility--getting-started)
- [Notes (plan & thought process)](#notes-plan--thought-process)

---

## Architecture Overview

> Source file: [`docs/architecture.drawio`](docs/architecture.drawio) (editable in [draw.io](https://app.diagrams.net/); exported PNGs below).

![High-Level Architecture](docs/High-Level%20Architecture_drawio_image.png)

### Why ELT (not ETL)?

**ELT** (Extract–Load–Transform) has been adopted so that transformations remain inside the warehouse: raw CSVs are loaded into S3 and PostgreSQL's `raw` schema, and dbt then handles staging, intermediate, and marts in SQL. A single source of truth is preserved, and business logic can be changed and re-run without modifying the load step.

---

## Tech Stack

| Layer            | Tool                                   | Purpose                                                          |
| ---------------- | -------------------------------------- | ---------------------------------------------------------------- |
| Language         | Python 3.10+                           | Scripting, EL tasks, Airflow DAGs                                |
| SQL              | PostgreSQL 15                          | Warehouse queries, dbt backend                                   |
| Transformations  | dbt Core + dbt-postgres                | Medallion architecture (raw → staging → intermediate → marts)    |
| Orchestration    | Apache Airflow 2.x + astronomer-cosmos | Centralized scheduling, workflow automation, dbt task visibility |
| Dashboard        | Tableau Public                         | Interactive analytics dashboard (public URL)                     |
| Containerization | Docker + Docker Compose                | Reproducible deployment (Airflow + PostgreSQL + dbt)             |
| Cloud            | AWS EC2 + S3                           | Hosting (EC2), Data Lake (S3)                                    |
| Version Control  | Git + GitHub                           | Source control                                                   |
| Secrets          | `.env` (Docker env vars)               | Local config; Secrets Manager recommended for production         |

---

## Project Structure

```
final_project/
├── README.md                            # This file — project overview & setup
├── .gitignore
├── requirements.txt
│
├── data/                                # Raw CSVs (gitignored)
│   ├── policy.csv
│   ├── invoice.csv
│   └── claim.csv
│
├── notebooks/                           # Exploratory Data Analysis
│   └── eda_summary.ipynb
│
├── notes/                               # Plan & thought process (shared with reviewers)
│   ├── setup_guide.md                   # Phase-by-phase setup and build order
│   └── tableau_summary.md               # Tableau workbook structure and data sources
│
├── docs/                                # Architecture diagrams
│   └── architecture.drawio
│
├── dbt_project/                         # dbt transformations
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── staging/                     # Bronze → Silver (clean + type cast)
│   │   ├── intermediate/                # Business logic layer
│   │   └── marts/                       # Gold (analytical models)
│   ├── tests/
│   └── macros/
│
├── airflow/                             # Orchestration
│   ├── dags/
│   │   └── insurance_elt_pipeline.py
│   └── plugins/
│
├── dashboard/                           # Analytics Dashboard (Tableau)
│   └── README.md                        # Public URL + screenshots
│
├── infra/                               # Docker & Cloud deployment
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── .env.example
│   ├── INFRA.md                         # Local Docker + cloud architecture
│   ├── scripts/
│   │   └── init_warehouse.sql
│   └── ...
│
└── scripts/                             # Python EL scripts
    ├── extract_load.py                  # CSV → S3 → PostgreSQL (raw schema)
    └── upload_to_s3.py                  # Upload local CSVs to S3
```

---

## Data Sources

Three CSVs: policy (~6.6k rows), invoice (~9.6k), claim (~792). They link on `policy_number`; `user_id` in policy is the customer (one user can have many policies). Details in the EDA notebook.

---

## Exploratory Data Analysis

EDA was conducted in [`notebooks/eda_summary.ipynb`](notebooks/eda_summary.ipynb) before SQL or dbt so that model design would match the data.

Key findings: 6,583 policies (9 product types, 166 users; outpatient dominates). One user holds 5,380 policies and is treated as an outlier (excluded in staging). Invoices and claims link on `policy_number`; two orphan invoices are handled via referential checks in dbt. New vs returning is defined using `ROW_NUMBER()` over `effective_date` per user. These findings inform staging logic, null handling, and analytical definitions.

---

## Data Ingestion & Orchestration

A single Airflow DAG (`insurance_elt_pipeline`) runs the full ELT flow end-to-end:

1. **Extract & Load** — a Python script (`scripts/extract_load.py`) reads CSVs from S3 (or local `data/`) and loads them into PostgreSQL's `raw` schema.
2. **Transform** — `dbt run` builds the staging → intermediate → marts layers.
3. **Test** — `dbt test` validates data quality (not-null, unique, referential integrity).

**astronomer-cosmos** renders each dbt model as an individual Airflow task with correct dependencies, giving full visibility into the DAG.

![ELT Pipeline (Airflow DAG)](<docs/ELT%20Pipeline%20(Airflow%20DAG)_drawio_image.png>)

---

## Data Warehouse & Data Model

The data warehouse uses a **medallion layout** in PostgreSQL: `raw` (load as-is), then `staging` (clean and type), `intermediate` (business logic), and `marts` (reporting). Tables are organized into **separate schemas** matching each layer for clear isolation.

| Layer      | Schema         | What's in it                                                                                     |
| ---------- | -------------- | ------------------------------------------------------------------------------------------------ |
| **Bronze** | `raw`          | `raw_policy`, `raw_invoice`, `raw_claim`                                                         |
| **Silver** | `staging`      | `stg_policy`, `stg_invoice`, `stg_claim`                                                         |
| **Silver** | `intermediate` | `int_policy_ranked`, `int_invoice_paid`                                                          |
| **Gold**   | `marts`        | New vs returning, denormalized policy, and dashboard marts (daily, rollups, monthly, by product) |

![Data Model Lineage](docs/Data%20Model%20Lineage_drawio_image.png)

---

## Transformations (dbt)

All transformations are defined in **dbt Core** with the `dbt-postgres` adapter, following the medallion architecture:

- **Staging models** (`stg_policy`, `stg_invoice`, `stg_claim`): clean column names, cast types, filter outliers, add referential checks.
- **Intermediate models** (`int_policy_ranked`, `int_invoice_paid`): business logic such as identifying new vs returning customers via `ROW_NUMBER()` and filtering to paid invoices.
- **Mart models**: analytical tables consumed by the dashboard — `mart_new_vs_returning_premium`, `mart_policy_denormalized`, `mart_dashboard_daily`, `mart_dashboard_monthly`, `mart_dashboard_rollups`, `mart_dashboard_by_product`.

dbt tests enforce not-null, uniqueness, accepted values, and referential integrity. A custom macro (`generate_schema_name`) routes models to the correct PostgreSQL schema.

---

## Dashboard

**[Live Dashboard →](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link)**

A Tableau Story with **4 interactive dashboards**:

| Dashboard                     | What it shows                                                                                                              |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Performance Dashboard**     | KPIs, monthly premium vs claims trend, product breakdown, loss ratio, new vs returning, policies issued                    |
| **Executive Summary**         | Quarterly & annual performance table with YoY % growth                                                                     |
| **Claims Analysis**           | Billed vs payable, coverage ratio, claim rate & frequency, out-of-pocket, top costliest policies, profitability by product |
| **Customer & Policy Profile** | Age distribution, premium & loss ratio by age group, revenue per invoice, product × gender heatmap                         |

Metrics are pre-computed in dbt marts so the dashboard uses `mart_dashboard_monthly`, `mart_dashboard_rollups`, `mart_dashboard_by_product`, `mart_new_vs_returning_premium`, and `mart_policy_denormalized` without heavy calculated fields. Details in [dashboard/README.md](dashboard/README.md).

---

## Cloud Infrastructure

The entire stack is deployed on **AWS**:

| Service            | Role                                                                         |
| ------------------ | ---------------------------------------------------------------------------- |
| **S3**             | Data lake — raw CSVs stored under `raw/` prefix                              |
| **EC2** (t3.small) | Hosts Airflow, PostgreSQL (warehouse + metadata), and dbt via Docker Compose |

The same `docker-compose.yml` used locally runs on EC2 with no changes. Security, reliability, and cost (~$0–10/month on free tier) are documented in [`infra/INFRA.md`](infra/INFRA.md). IaC-style deployment scripts are in `infra/scripts/`.

---

## Reproducibility / Getting Started

Local setup requires Python 3.10+, PostgreSQL 15, Docker Compose, dbt-core + dbt-postgres, and AWS CLI when using S3/EC2.

**Local run (no Docker):** Clone the repo, run `pip install -r requirements.txt`, copy `infra/.env.example` to `.env` and set Postgres (and AWS if needed). Then run `python scripts/extract_load.py` and from `dbt_project`: `dbt deps`, `dbt run`, `dbt test`.

**Full pipeline (Docker):** From the repo root, `cd infra` and `docker compose --env-file ../.env up -d` (so root `.env` is loaded). On first run the init container creates the Airflow DB and admin user; after ~30–60 seconds the UI is available at http://localhost:8082 (login `admin` / `admin`). The `insurance_elt_pipeline` DAG runs the full ELT when triggered.

**S3 (pipeline reads CSVs from S3):** Create a bucket, set `S3_BUCKET_NAME` in `.env`, then run `python scripts/upload_to_s3.py` from the repo root to upload `data/*.csv` under `raw/`. See [infra/S3_SETUP.md](infra/S3_SETUP.md).

---

## Notes (plan & thought process)

The [`notes/`](notes/) folder is included so that build order and decisions are visible to reviewers:

| File                                           | Content                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| [setup_guide.md](notes/setup_guide.md)         | Phase-by-phase setup (PostgreSQL, S3, dbt, Airflow, EC2) and build order. |
| [tableau_summary.md](notes/tableau_summary.md) | Workbook structure, marts used per sheet, and metrics.                    |
