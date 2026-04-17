# Streaming path (PyFlink + Kafka → Postgres)

This is the **minimal stream ingestion** leg for the course project: synthetic **policy-style events** are published to **Kafka**, consumed by a **PyFlink** job, and written into **`raw_streaming.stream_policy_events`** in the same PostgreSQL warehouse used by the batch ELT pipeline.

The **batch pipeline** (CSV → S3 → `raw` → Airflow → dbt → `marts`) is unchanged. A future **dbt v2** could add `staging` models sourced from `raw_streaming`; that is not required for the demo mart described in the root README.

## What runs where

| Piece | Role |
|--------|------|
| `zookeeper` + `kafka` | Message bus |
| `kafka-init` | Creates topic `policy_events` once |
| `event-producer` | Sends JSON events every few seconds |
| `flink-streaming` | PyFlink DataStream job: Kafka → JDBC → `raw_streaming.stream_policy_events` |

## First-time database setup

- **New warehouse volume:** `infra/scripts/init_warehouse.sql` already creates `raw_streaming.stream_policy_events`.
- **Existing Postgres (e.g. EC2) already initialized:** run once:

  ```bash
  psql -h <host> -U <POSTGRES_USER> -d insurance_dwh -f infra/scripts/add_raw_streaming.sql
  ```

## Start with Docker Compose

From `final_project/infra/` (with root `.env` populated like the rest of the project):

```bash
docker compose --env-file ../.env up -d
```

Services `event-producer` and `flink-streaming` start after `kafka-init` completes.

## Verify rows

```bash
docker compose --env-file ../.env exec warehouse \
  sh -c 'psql -U "$POSTGRES_USER" -d insurance_dwh \
  -c "SELECT COUNT(*), MAX(received_at) FROM raw_streaming.stream_policy_events;"'
```

(`sh -c` expands `POSTGRES_USER` inside the container; `$POSTGRES_USER` on the host is often empty.)

**Operational notes**

- **`flink-streaming`** loads connector JARs from `/opt/flink/lib` (includes **`kafka-clients`** for the Kafka consumer). After changing [`Dockerfile`](Dockerfile), rebuild:  
  `docker compose --env-file ../.env build flink-streaming && docker compose --env-file ../.env up -d flink-streaming`.
- Check logs if the table stays empty or the Flink container restarts:  
  `docker compose --env-file ../.env logs -f flink-streaming event-producer`.

## Local producer only (without Compose streaming services)

If Kafka is exposed on `localhost:9092`:

```bash
pip install kafka-python
set KAFKA_BOOTSTRAP_SERVERS=localhost:9092
python producer.py
```

## Stop streaming services only

There is no separate profile in this step; scale to zero if needed:

```bash
docker compose --env-file ../.env stop event-producer flink-streaming
```

Kafka/Zookeeper can stay up for faster restarts.
