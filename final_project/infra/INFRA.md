# Infrastructure: Airflow + Docker (Local) & Cloud

This folder runs the full ELT: **extract_load** (S3 or local `data/` → Postgres `raw`), then **dbt run** and **dbt test**, orchestrated by Airflow, plus an optional **Streamlit** service (Text-to-SQL on port **8501**).

## Requirements

- Docker and Docker Compose
- Root **`.env`** (copy from `infra/.env.example`; never commit `.env`): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` (default **`warehouse`** — the warehouse Postgres service in this compose)
- **`dbt_project/profiles.yml`** — only for **local** `dbt run` from your laptop. **Airflow on Docker/EC2** does not use it: the DAG uses `profiles.yml.example` and a writable `/tmp` copy (see below).
- **Data:** either set **`S3_BUCKET_NAME`** (and optional **`S3_RAW_PREFIX`**, default `raw`) in `.env`, or place the three CSVs in **`data/`** (see [S3_SETUP.md](S3_SETUP.md)). **`data/` is gitignored** — on EC2 you almost always use **S3**; without S3 and without CSVs in `data/`, extract_load skips all files and dbt may fail on empty raw tables.
- On **EC2**, attach an IAM role with S3 read access when using S3 (no access keys in `.env` on the server)

## Run locally

From repo root:

```bash
cd dbt_project && cp profiles.yml.example profiles.yml   # once if needed
cd ../infra && docker compose --env-file ../.env up -d
```

`.env` lives in the **repo root**; Compose only auto-loads `.env` in `infra/`, so use **`--env-file ../.env`** (or copy `.env` into `infra/`). On Linux EC2, if Docker says permission denied on `docker.sock`, run `sudo usermod -aG docker ubuntu`, log out/in, or use `sudo docker compose ...`.

First run: init creates Airflow metadata and admin user. After ~30–60s: **http://localhost:8082** — `admin` / `admin`. Trigger DAG **`insurance_elt_pipeline`**.

**Streamlit:** With the same compose, `http://localhost:8501` locally or `http://<Elastic-IP>:8501` on EC2. The container uses **`POSTGRES_HOST=warehouse`** on the Docker network; add **`OPENROUTER_API_KEY`** (and optionally `OPENROUTER_MODEL`) to root `.env` so the app can call OpenRouter. Rebuild after Dockerfile changes: `docker compose --env-file ../.env build streamlit && docker compose --env-file ../.env up -d`.

## Architecture

| Service   | Role |
|-----------|------|
| **postgres** | Airflow metadata DB only |
| **warehouse** | PostgreSQL for **insurance_dwh** (dbt + extract_load) |
| **airflow-*** | Scheduler + webserver; mounts `airflow/dags`, `scripts`, `data`, `dbt_project`, root `.env` |
| **streamlit** | Text-to-SQL UI; image from `Dockerfile.streamlit`; connects to **warehouse**; publishes **8501** |

Default **`POSTGRES_HOST=warehouse`**. To use Postgres on your laptop instead, set **`POSTGRES_HOST=host.docker.internal`** in `.env` and add under Airflow services in `docker-compose.yml` if on Linux:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## EC2

Same compose. **Security group inbound:** **8082** (Airflow UI), **8501** (Streamlit), **5432** (Postgres, if reviewers connect from outside), **22** (SSH). Use the **same Elastic IP** for Airflow and Streamlit — reviewers open `http://<Elastic-IP>:8082` and `http://<Elastic-IP>:8501`.

Set `.env` on the instance with **`POSTGRES_HOST=warehouse`** (required for containers to reach the warehouse; do not use `localhost` on EC2 for Airflow). Include **`OPENROUTER_API_KEY`** for Streamlit. If using S3, set **`S3_BUCKET_NAME`**. See [S3_SETUP.md](S3_SETUP.md).

### ⚠️ Disk space (important)

**The default root volume (often 8 GB) is too small.** With Airflow, two Postgres instances, dbt, and logs, the disk fills and Postgres/Airflow fail (“could not write init file”, DAGs disappear, unhealthy containers). **Use at least 30 GB for the root EBS volume.**

- **At launch:** When creating the instance, set root volume size to **30** (or **50**) GB.
- **Existing instance:** EC2 → Volumes → select the instance’s volume → **Modify volume** → set size to **30** (or **50**) GB → Modify. After the volume shows “optimizing”/completed, on the instance run:
  ```bash
  sudo growpart /dev/nvme0n1 1
  sudo resize2fs /dev/nvme0n1p1
  ```
  (Use `lsblk` to confirm device names; use `xvda` / `xvda1` if your instance uses that.) Then `df -h` should show the new space.

### Gitignored files vs EC2 (checklist)

| Item | In git? | Needed on EC2? |
|------|---------|----------------|
| **`.env`** (repo root) | No | **Yes.** Create from `.env.example`. Compose needs `--env-file ../.env`. Without it, warehouse credentials and S3 settings are missing. |
| **`dbt_project/profiles.yml`** | No | **No for Airflow.** DAG uses `profiles.yml.example` + `/tmp`. Yes if you run `dbt` manually on the server. |
| **`data/*.csv`** | No | **Only if not using S3.** With `S3_BUCKET_NAME` set + IAM role, CSVs come from S3. |
| **`dbt_project/target/`, `dbt_packages/`, `logs/`** | No | **No.** Created at runtime; DAG runs dbt from a copy under `/tmp` so the bind-mounted project stays read-only for the `airflow` user. |
| **`docker-compose.override.yml`** | No | Optional local overrides only. |
| **`*.twbx`** (Tableau) | No | Optional deliverable; not used by the pipeline. |

## Connecting to the warehouse (Tableau, pgAdmin)

The **warehouse** container exposes **port 5432** on the host so you can connect from your laptop.

1. **EC2 security group:** Add inbound rules as needed: **Custom TCP 8501** (Streamlit), **PostgreSQL 5432** (optional external DB tools), **Custom TCP 8082** (Airflow). Prefer **My IP** / a tight CIDR (avoid **0.0.0.0/0** except for short demos).
2. **Restart the stack** so the port is published (if you just added `ports: 5432` to the compose):
   ```bash
   cd infra && sudo docker compose --env-file ../.env up -d
   ```

Use the **same credentials as in your root `.env`** on the server:

| Field    | Value |
|----------|--------|
| **Host** | EC2 Elastic IP `52.221.114.40` (or current public IP if it changes) |
| **Port** | `5432` |
| **Database** | `insurance_dwh` (or `POSTGRES_DB` from `.env`) |
| **User** | `POSTGRES_USER` from `.env` |
| **Password** | `POSTGRES_PASSWORD` from `.env` |

**pgAdmin:** New Server → General: name e.g. `insurance_dwh_ec2` → Connection: host = EC2 IP, port 5432, database `insurance_dwh`, username/password from above. Then browse **Schemas** → **raw**, **staging**, **intermediate**, **marts** to see tables/views from dbt.

**Tableau:** Connect to **PostgreSQL** → enter the same host, port, database, user, password. Use tables/views from **marts** (and other schemas) as data sources.
