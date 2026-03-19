# Bennis Yiu | Data Engineer Technical Assessment

> Technical Assessment for Data Engineer Position at Bowtie Life Insurance Co. Ltd.

---

## Access for Reviewers

| What                    | Where                                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------------------------- |
| Code, SQL, dbt models   | This repo                                                                                             |
| Setup and Tableau notes | [`notes/`](notes/) (setup_guide.md, tableau_summary.md)                                               |
| Airflow UI (on EC2)     | `http://18.142.43.130:8082` — `admin` / `admin` (see [`Q2_infra/INFRA.md`](Q2_infra/INFRA.md))        |
| Database (PostgreSQL)   | `18.142.43.130:5432` / `insurance_dwh` — read-only credentials shared via email (see below)           |
| Tableau dashboard       | [Insurance Policy, Claims & Invoice Analytics](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link) (4 dashboards as a Story) |
| Architecture diagrams   | [High-Level](docs/High-Level%20Architecture_drawio_image.png), [ELT Pipeline](<docs/ELT Pipeline (Airflow DAG)_drawio_image.png>), [Data Lineage](docs/Data%20Model%20Lineage_drawio_image.png) |
| Docker & cloud          | [`Q2_infra/INFRA.md`](Q2_infra/INFRA.md). **EC2:** use ≥30 GB root volume (default 8 GB fills and breaks the pipeline). |

---

## Table of Contents

- [Access for Reviewers](#access-for-reviewers)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Sources](#data-sources)
- [Exploratory Data Analysis](#exploratory-data-analysis)
- [ELT Pipeline](#elt-pipeline)
- [Data Model](#data-model)
- [Deliverables](#deliverables)
  - [Q1: Analytics Engineering](#q1-analytics-engineering)
  - [Q2: Data Pipeline & Orchestration](#q2-data-pipeline--orchestration)
  - [Q3: Analytics Dashboard](#q3-analytics-dashboard)
  - [Bonus: Cloud Infrastructure](#bonus-cloud-infrastructure)
- [Getting Started](#getting-started)
- [Notes (plan & thought process)](#notes-plan--thought-process)

Deliverable locations:

| Question                          | Where it lives                                                         |
| --------------------------------- | ---------------------------------------------------------------------- |
| **Q1** — Analytics Engineering    | [`Q1_sql/`](Q1_sql/) (q1a, q1b) and `dbt_project/models/`              |
| **Q2** — Pipeline & Orchestration | `airflow/dags/`, `scripts/`, [`Q2_infra/`](Q2_infra/) (Docker + cloud) |
| **Q3** — Analytics Dashboard      | [`Q3_dashboard/`](Q3_dashboard/) and `notes/tableau_summary.md`        |

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
| Version Control  | Git + GitHub                           | Private repo with collaborator access                            |
| Secrets          | `.env` (Docker env vars)               | Local config; Secrets Manager recommended for production         |

---

## Project Structure

```
Bennis_Yiu_Data_Engineer_Technical_Assessment/
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
├── Q1_sql/                              # Q1: Analytics Engineering (answer SQL)
│   ├── q1a_new_vs_returning_premium.sql
│   └── q1b_denormalized_models.sql
│
├── dbt_project/                         # Q1 + Q2: dbt transformations
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
├── airflow/                             # Q2: Orchestration
│   ├── dags/
│   │   └── insurance_elt_pipeline.py
│   └── plugins/
│
├── Q3_dashboard/                        # Q3: Analytics Dashboard (Tableau)
│   └── README.md                        # Public URL + screenshots
│
├── Q2_infra/                            # Q2 + Bonus: Docker & Cloud deployment
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── .env.example
│   ├── INFRA.md                         # Local Docker + cloud architecture
│   ├── scripts/
│   │   ├── init_db.sql
│   │   ├── setup_ec2.sh
│   │   └── deploy.sh
│   └── ...
│
└── scripts/                             # Python EL scripts
    ├── extract_load.py                  # CSV → S3 → PostgreSQL (raw schema)
    └── utils.py                         # Shared helpers
```

---

## Data Sources

Three CSVs: policy (~6.6k rows), invoice (~9.6k), claim (~792). They link on `policy_number`; `user_id` in policy is the customer (one user can have many policies). Details in the EDA notebook.

---

## Exploratory Data Analysis

EDA was conducted in [`notebooks/eda_summary.ipynb`](notebooks/eda_summary.ipynb) before SQL or dbt so that model design would match the data.

Key findings: 6,583 policies (9 product types, 166 users; outpatient dominates). One user holds 5,380 policies and is treated as an outlier (excluded in staging). Invoices and claims link on `policy_number`; two orphan invoices are handled via referential checks in dbt. New vs returning is defined using `ROW_NUMBER()` over `effective_date` per user. These findings inform staging logic, null handling, and Q1 definitions.

---

## ELT Pipeline

A single Airflow DAG runs the full flow. astronomer-cosmos is used so that each dbt model is rendered as an Airflow task with dependencies.

![ELT Pipeline (Airflow DAG)](<docs/ELT%20Pipeline%20(Airflow%20DAG)_drawio_image.png>)

---

## Data Model

The data warehouse uses a **medallion layout** in PostgreSQL: `raw` (load as-is), then `staging` (clean and type), `intermediate` (business logic), and `marts` (reporting).

| Layer      | Schema         | What's in it                                                                                     |
| ---------- | -------------- | ------------------------------------------------------------------------------------------------ |
| **Bronze** | `raw`          | `raw_policy`, `raw_invoice`, `raw_claim`                                                         |
| **Silver** | `staging`      | `stg_policy`, `stg_invoice`, `stg_claim`                                                         |
| **Silver** | `intermediate` | `int_policy_ranked`, `int_invoice_paid`                                                          |
| **Gold**   | `marts`        | New vs returning, denormalized policy, and dashboard marts (daily, rollups, monthly, by product) |

![Data Model Lineage](docs/Data%20Model%20Lineage_drawio_image.png)

---

## Deliverables

### Q1: Analytics Engineering

Standalone SQL: [`Q1_sql/q1a_new_vs_returning_premium.sql`](Q1_sql/q1a_new_vs_returning_premium.sql) and [`Q1_sql/q1b_denormalized_models.sql`](Q1_sql/q1b_denormalized_models.sql). The same logic lives in dbt as [`mart_new_vs_returning_premium`](dbt_project/models/marts/mart_new_vs_returning_premium.sql) and [`mart_policy_denormalized`](dbt_project/models/marts/mart_policy_denormalized.sql). Q1a compares average net premium for new (first policy per user) vs returning (same user's 2nd+ policy). Q1b denormalizes policy, invoice, and claim into analytical models.

### Q2: Data Pipeline & Orchestration

A single Airflow DAG runs extract_load (Python), then dbt run and dbt test. astronomer-cosmos is used so that each dbt model is a task with dependencies. The Python script performs CSV → S3 and S3 → PostgreSQL `raw`; the stack runs in Docker Compose for reproducible execution locally and on EC2.

### Q3: Analytics Dashboard

**[Live Dashboard →](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link)** — A Tableau Story with 4 interactive dashboards: Performance Overview, Executive Summary (Q/Y with YoY %), Claims Analysis (coverage, claim rates, profitability), and Customer & Policy Profile (age, gender, product breakdowns). Metrics are pre-computed in dbt marts so the dashboard uses `mart_dashboard_monthly`, `mart_dashboard_rollups`, `mart_dashboard_by_product`, `mart_new_vs_returning_premium`, and `mart_policy_denormalized` without heavy calculated fields. Details in [Q3_dashboard/README.md](Q3_dashboard/README.md).

### Bonus: Cloud Infrastructure

The same Docker Compose stack is deployed on AWS: S3 for raw CSVs, EC2 (t3.micro) for Airflow, Postgres metadata DB, and dbt. Security, reliability, and cost (~$0–10/month on free tier) are documented in [`Q2_infra/INFRA.md`](Q2_infra/INFRA.md).

---

## Notes (plan & thought process)

The [`notes/`](notes/) folder is included so that build order and decisions are visible to reviewers:

| File                                           | Content                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| [setup_guide.md](notes/setup_guide.md)         | Phase-by-phase setup (PostgreSQL, S3, dbt, Airflow, EC2) and build order. |
| [tableau_summary.md](notes/tableau_summary.md) | Workbook structure, marts used per sheet, and metrics.                    |

---

## Getting Started

Local setup requires Python 3.10+, PostgreSQL 15, Docker Compose, dbt-core + dbt-postgres, and AWS CLI when using S3/EC2.

**Local run (no Docker):** Clone the repo, run `pip install -r requirements.txt`, copy `Q2_infra/.env.example` to `.env` and set Postgres (and AWS if needed). Then run `python scripts/extract_load.py` and from `dbt_project`: `dbt deps`, `dbt run`, `dbt test`.

**Full pipeline (Docker):** From the repo root, `cd Q2_infra` and `docker compose --env-file ../.env up -d` (so root `.env` is loaded). On first run the init container creates the Airflow DB and admin user; after ~30–60 seconds the UI is available at http://localhost:8082 (login `admin` / `admin`). The `insurance_elt_pipeline` DAG runs the full ELT when triggered.

**S3 (pipeline reads CSVs from S3):** Create a bucket, set `S3_BUCKET_NAME` in `.env`, then run `python scripts/upload_to_s3.py` from the repo root to upload `data/*.csv` under `raw/`. See [Q2_infra/S3_SETUP.md](Q2_infra/S3_SETUP.md).
