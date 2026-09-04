# Railway deployment

This directory contains the immutable images and entrypoints used to run the
insurance analytics portfolio on Railway. The original AWS/EC2 Docker Compose
deployment remains in `infra/docker-compose.yml`.

Before approving permanent AWS deletion, complete
[`ACCEPTANCE_TEST.md`](ACCEPTANCE_TEST.md).

## Cost-aware production services

| Service | Source | Runtime |
|---|---|---|
| `Postgres` | Railway PostgreSQL 15 | Always on, private |
| `streamlit` | `infra/Dockerfile.streamlit` | Public, serverless sleep enabled |
| `elt-pipeline` | `infra/railway/Dockerfile.pipeline` | Weekly Railway cron |
| `insurance-raw-data` | Railway Storage Bucket | Private S3-compatible storage |

Railway should use `/final_project` as the repository root. Inter-service
traffic uses private Railway networking. PostgreSQL does not need a public TCP
proxy.

### Pipeline variables

- `ADMIN_DATABASE_URL` references `Postgres.DATABASE_URL`
- `PIPELINE_DATABASE_URL` uses the generated `pipeline_writer` login
- `PIPELINE_DB_USER` / `PIPELINE_DB_PASSWORD`
- `STREAMLIT_DB_USER` / `STREAMLIT_DB_PASSWORD` (used to create the reader)
- `S3_BUCKET_NAME` references bucket `BUCKET`
- `S3_ENDPOINT_URL` references bucket `ENDPOINT`
- `AWS_ACCESS_KEY_ID` references bucket `ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY` references bucket `SECRET_ACCESS_KEY`
- `AWS_REGION` references bucket `REGION`
- `S3_RAW_PREFIX=raw`
- `SEED_BUCKET_ON_START=true`

`run_pipeline.py` initializes schemas and roles, uploads the bundled source
CSVs to the Railway bucket, atomically refreshes raw tables, runs `dbt build`,
and exits. The production schedule is `0 3 * * 0` (Sunday 03:00 UTC).

### Streamlit variables

- `STREAMLIT_DATABASE_URL` uses the generated `streamlit_reader` login
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_NAME`

Add `OPENROUTER_API_KEY` in the `streamlit` service's Railway **Variables**
tab. Never commit its value to `.env` or Git.

The reader login has access only to `marts`, defaults to read-only
transactions, has a 15-second statement timeout, and is limited to five
connections.

## On-demand Airflow demo

Airflow remains fully runnable on Railway but is not kept online continuously.
Create two services from the same GitHub repository and branch:

| Service | Dockerfile | Start variable |
|---|---|---|
| `airflow-webserver` | `infra/railway/Dockerfile.airflow` | `AIRFLOW_ROLE=webserver` |
| `airflow-scheduler` | `infra/railway/Dockerfile.airflow` | `AIRFLOW_ROLE=scheduler` |

Both use `/final_project` as the root and share:

- `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` using the generated `airflow_user`
  login and the `airflow` logical database
- Warehouse `POSTGRES_*` variables using `pipeline_writer`
- Railway bucket variables listed above
- A generated `AIRFLOW__WEBSERVER__SECRET_KEY`

The webserver also receives generated `AIRFLOW_ADMIN_PASSWORD` and is the only
Airflow service given a public domain:
https://airflow-webserver-production-be4b.up.railway.app. It responds only
while demo mode is enabled. The scheduler unpauses `insurance_elt_pipeline`
when `AIRFLOW_UNPAUSE_DAG=true`.

Both services default to `DEMO_MODE=false`, so their containers exit immediately
without consuming idle compute. Set `DEMO_MODE=true` and redeploy to demonstrate
Airflow; restore `false` and redeploy afterward. The Airflow metadata database
remains in the existing PostgreSQL service for the next demo.

## On-demand Kafka and Flink demo

Create these temporary Railway services:

| Service | Source |
|---|---|
| `zookeeper` | `infra/railway/Dockerfile.zookeeper` |
| `kafka` | `infra/railway/Dockerfile.kafka` |
| `event-producer` | `infra/railway/Dockerfile.producer` |
| `flink-streaming` | `infra/railway/Dockerfile.flink` |

Use private networking only. Kafka listens on `29092` internally and advertises
its Railway private domain. The producer and Flink job use
`KAFKA_BOOTSTRAP_SERVERS=<kafka-private-domain>:29092` and
`KAFKA_TOPIC=policy_events`. Flink uses the `pipeline_writer` PostgreSQL
credentials and writes to `raw_streaming.stream_policy_events`.

Verification:

1. Start ZooKeeper, then Kafka.
2. Start the producer and Flink services.
3. Confirm new rows arrive in `raw_streaming.stream_policy_events`.
4. Capture the demonstration evidence.
5. Set `DEMO_MODE=false` on all four services and redeploy. Their entrypoints
   exit successfully, leaving the Railway service definitions in place without
   continuous compute charges.

The stream is intentionally a landing-zone demonstration; current dbt marts do
not consume it.

## Deployment verification

The production migration was exercised end to end on 2026-09-04:

- Streamlit reported healthy after its Railway database and OpenRouter
  variables were configured.
- The scheduled pipeline uploaded all three source CSVs, loaded 6,583 policies,
  9,646 invoices, and 791 claims, then passed all 29 dbt models/tests.
- Airflow initialized its dedicated metadata database; both the metadatabase
  and scheduler reported healthy through the webserver health endpoint.
- ZooKeeper and Kafka started over Railway private networking, the producer
  published policy events, and the PyFlink Kafka-to-JDBC job launched.
- The backup job uploaded a logical PostgreSQL dump under `backups/` in the
  Railway bucket.
- All Airflow and streaming services were returned to `DEMO_MODE=false`, and
  PostgreSQL was left without a public TCP proxy.

## Cost controls

AWS Cost Explorer reported about US$26.24 for August 2026 across the service
categories supporting the original deployment. This Railway layout is designed
to stay near the Hobby plan's US$5 monthly usage allowance:

- Keep Streamlit serverless and do not attach an uptime monitor.
- Keep the pipeline weekly or manual because the source dataset is static.
- Apply per-service CPU and memory ceilings.
- Configure a soft usage alert around USD 4. Railway's minimum compute hard
  limit is USD 10, so the platform cannot enforce a USD 5 hard stop.
- Do not leave Airflow, Kafka, ZooKeeper, Flink, or the producer running after
  a demonstration.

## Backup and recovery

The warehouse is reproducible from the Railway bucket plus dbt. Also retain a
logical `pg_dump` outside Railway before decommissioning AWS and periodically
afterward. Test one restore before removing the EC2 volume and S3 bucket.
