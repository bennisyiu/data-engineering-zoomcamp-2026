# Data Engineering Zoomcamp 2026

Coursework and capstone for [Data Engineering Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp): homework by module, plus a completed **final project** (insurance analytics ELT on AWS).

## Final project (capstone)

**[Insurance Policy Analytics](final_project/README.md)** — End-to-end **ELT**: Python extract/load (S3 → PostgreSQL), **dbt** (medallion: raw → staging → intermediate → marts), **Apache Airflow** orchestration, **AWS EC2 + S3**, and a **Tableau Public** dashboard.

Reviewers: start at [`final_project/README.md`](final_project/README.md) for access (Airflow UI, warehouse connection, live dashboard, architecture diagrams, and infra notes).

---

## Environment

Homework and the project use **Python** with a local **venv** and **pip** (not `uv`). Commands in module notes assume familiarity with **Windows PowerShell** where relevant.

Each module folder includes its own **`requirements.txt`** (and often a `*.md` homework write-up).

---

## Modules in this repository

| Module | Topic | Notes / entry point |
|--------|--------|---------------------|
| 1 | Docker & Terraform | [`module_1_docker_terraform/module1.md`](module_1_docker_terraform/module1.md) |
| 2 | Workflow orchestration | [`module_2_workflow_orchestration/module2.md`](module_2_workflow_orchestration/module2.md) |
| 3 | Data warehouse | BigQuery homework SQL and scripts in [`module_3_data_warehouse/`](module_3_data_warehouse/) |
| 4 | Analytics engineering | [`module_4_anlytics_engineering/module4_setup.md`](module_4_anlytics_engineering/module4_setup.md) |
| 5 | Streaming | *(not present as a folder in this repo)* |
| 6 | Batch processing | [`module_6_batch_processing/module_6.md`](module_6_batch_processing/module_6.md) |

The Zoomcamp curriculum also lists Module 5 (streaming); only the folders above are included here.

---

## Repository layout

```
data-engineering-zoomcamp-2026/
├── README.md
├── final_project/                 # Capstone — README, dbt, Airflow, infra, dashboard notes
├── module_1_docker_terraform/
├── module_2_workflow_orchestration/
├── module_3_data_warehouse/
├── module_4_anlytics_engineering/
├── module_6_batch_processing/
└── .gitignore
```
