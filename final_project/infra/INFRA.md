# Infrastructure: Airflow + Docker (Local) & Cloud

This folder runs the full ELT: **extract_load** (S3 or local `data/` → Postgres `raw`), then **dbt run** and **dbt test**, orchestrated by Airflow.

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

## Architecture

| Service   | Role |
|-----------|------|
| **postgres** | Airflow metadata DB only |
| **warehouse** | PostgreSQL for **insurance_dwh** (dbt + extract_load) |
| **airflow-*** | Scheduler + webserver; mounts `airflow/dags`, `scripts`, `data`, `dbt_project`, root `.env` |

Default **`POSTGRES_HOST=warehouse`**. To use Postgres on your laptop instead, set **`POSTGRES_HOST=host.docker.internal`** in `.env` and add under Airflow services in `docker-compose.yml` if on Linux:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## EC2

Same compose; security group **8082** for Airflow UI. Set `.env` on the instance with warehouse credentials and, if using S3, **`S3_BUCKET_NAME`**. See [S3_SETUP.md](S3_SETUP.md).

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

1. **EC2 security group:** Add an **inbound rule**: Type **PostgreSQL**, Port **5432**, Source **My IP** (or **0.0.0.0/0** for testing only).
2. **Restart the stack** so the port is published (if you just added `ports: 5432` to the compose):
   ```bash
   cd infra && sudo docker compose --env-file ../.env up -d
   ```

Use the **same credentials as in your root `.env`** on the server:

| Field    | Value |
|----------|--------|
| **Host** | EC2 public IP (e.g. `18.142.43.130`) |
| **Port** | `5432` |
| **Database** | `insurance_dwh` (or `POSTGRES_DB` from `.env`) |
| **User** | `POSTGRES_USER` from `.env` |
| **Password** | `POSTGRES_PASSWORD` from `.env` |

**pgAdmin:** New Server → General: name e.g. `insurance_dwh_ec2` → Connection: host = EC2 IP, port 5432, database `insurance_dwh`, username/password from above. Then browse **Schemas** → **raw**, **staging**, **intermediate**, **marts** to see tables/views from dbt.

**Tableau:** Connect to **PostgreSQL** → enter the same host, port, database, user, password. Use tables/views from **marts** (and other schemas) as data sources.
