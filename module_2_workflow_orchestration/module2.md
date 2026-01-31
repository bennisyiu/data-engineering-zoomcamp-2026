## Module 2 - Workflow Orchestration with Kestra

Remarks: This module focuses on workflow orchestration using Kestra. The flows provided by the instructor have been adapted to work with BigQuery directly, as **my GCP service account does not have access to Cloud Storage (GCS)**. Files 06-09 have been modified to use a BigQuery-only approach as a workaround.

### Directory Setup

```
| data-engineering-zoomcamp-2026
|\_| module_2_workflow_orchestration
  |\_| flows
    |\_  01_hello_world.yaml
    |\_  02_python.yaml
    |\_  03_getting_started_data_pipeline.yaml
    |\_  04_postgres_taxi.yaml
    |\_  05_postgres_taxi_scheduled.yaml
    |\_  06_gcp_kv.yaml                    # Modified: GCP_BUCKET_NAME commented out
    |\_  07_gcp_setup.yaml                 # Modified: Removed GCS bucket creation
    |\_  08_gcp_taxi.yaml                  # Modified: BigQuery Load instead of GCS
    |\_  09_gcp_taxi_scheduled.yaml        # Modified: BigQuery Load instead of GCS
    |\_  10_chat_without_rag.yaml
    |\_  11_chat_with_rag.yaml
  |\_  docker-compose.yml
  |\_  Dockerfile
  |\_  module2.md
|\_  .gitignore
|\_  README.md
```

---

## Docker Compose Setup

The docker-compose.yml sets up the complete Kestra environment with PostgreSQL backends.

### Services

| Service         | Image              | Port       | Purpose                          |
| --------------- | ------------------ | ---------- | -------------------------------- |
| kestra          | kestra/kestra:v1.1 | 8080, 8081 | Workflow orchestration platform  |
| kestra_postgres | postgres:18        | -          | Kestra metadata storage          |
| pgdatabase      | postgres:18        | 5432       | NY Taxi data (for flows 04-05)   |
| pgadmin         | dpage/pgadmin4     | 8085       | PostgreSQL admin UI              |

### docker-compose.yml

```yaml
volumes:
  ny_taxi_postgres_data:
    driver: local
  kestra_postgres_data:
    driver: local
  kestra_data:
    driver: local

services:
  pgdatabase:
    image: postgres:18
    environment:
      POSTGRES_USER: root
      POSTGRES_PASSWORD: root
      POSTGRES_DB: ny_taxi
    ports:
      - "5432:5432"
    volumes:
      - ny_taxi_postgres_data:/var/lib/postgresql
    depends_on:
      kestra:
        condition: service_started

  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=root
    ports:
      - "8085:80"
    depends_on:
      pgdatabase:
        condition: service_started

  kestra_postgres:
    image: postgres:18
    volumes:
      - kestra_postgres_data:/var/lib/postgresql
    environment:
      POSTGRES_DB: kestra
      POSTGRES_USER: kestra
      POSTGRES_PASSWORD: k3str4
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d $${POSTGRES_DB} -U $${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 10

  kestra:
    image: kestra/kestra:v1.1
    pull_policy: always
    user: "root"
    command: server standalone
    volumes:
      - kestra_data:/app/storage
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/kestra-wd:/tmp/kestra-wd
    environment:
      KESTRA_CONFIGURATION: |
        datasources:
          postgres:
            url: jdbc:postgresql://kestra_postgres:5432/kestra
            driverClassName: org.postgresql.Driver
            username: kestra
            password: k3str4
        kestra:
          server:
            basicAuth:
              username: "admin@kestra.io"
              password: Admin1234!
          repository:
            type: postgres
          storage:
            type: local
            local:
              basePath: "/app/storage"
          queue:
            type: postgres
          tasks:
            tmpDir:
              path: /tmp/kestra-wd/tmp
          url: http://localhost:8080/
    ports:
      - "8080:8080"
      - "8081:8081"
    depends_on:
      kestra_postgres:
        condition: service_started
```

### Docker Compose Commands

```powershell
# Start all services
docker-compose up -d

# View running services
docker-compose ps

# View logs
docker-compose logs -f kestra

# Stop services
docker-compose down

# Stop and remove volumes (deletes all data!)
docker-compose down -v
```

### Access Points

| Service  | URL                   | Credentials                      |
| -------- | --------------------- | -------------------------------- |
| Kestra   | http://localhost:8080 | admin@kestra.io / Admin1234!    |
| pgAdmin  | http://localhost:8085 | admin@admin.com / root           |

---

## Kestra Flows Overview

### Learning Flows (01-03)

| Flow | Purpose |
| ---- | ------- |
| 01_hello_world | Basic flow with inputs, variables, logging, and scheduling |
| 02_python | Python script in Docker container with pip dependencies |
| 03_getting_started_data_pipeline | ETL: HTTP download, Python transform, DuckDB query |

### PostgreSQL Flows (04-05)

| Flow | Purpose |
| ---- | ------- |
| 04_postgres_taxi | Load NYC taxi data into local PostgreSQL (manual trigger) |
| 05_postgres_taxi_scheduled | Same as 04 but with cron scheduling and backfill support |

### GCP BigQuery Flows (06-09) - MODIFIED

> **NOTE TO INSTRUCTOR:** Files 06-09 have been modified from the original course materials.
> My GCP service account does not have access to Google Cloud Storage (GCS).
> As a workaround, I replaced the GCS-based external table approach with BigQuery's
> native Load task to directly load CSV data into BigQuery staging tables.

| Flow | Original Approach | My Modification |
| ---- | ----------------- | --------------- |
| 06_gcp_kv | Sets GCP config including bucket name | GCP_BUCKET_NAME commented out |
| 07_gcp_setup | Creates GCS bucket + BQ dataset | Only creates BQ dataset (no GCS) |
| 08_gcp_taxi | Upload to GCS -> External Table -> Transform | BigQuery Load -> Staging Table -> Transform |
| 09_gcp_taxi_scheduled | Same as 08 with scheduling | Same modification as 08 |

---

## GCP BigQuery Workaround Details

### Original Flow (requires GCS access)

```
Download CSV -> Upload to GCS bucket -> Create External Table (points to GCS) -> Transform -> Merge
```

### Modified Flow (BigQuery-only)

```
Download CSV -> BigQuery Load (to staging table) -> Transform -> Merge to final table
```

### Key Changes Made

**06_gcp_kv.yaml:**
- Commented out `GCP_BUCKET_NAME` key-value pair

**07_gcp_setup.yaml:**
- Removed `create_gcs_bucket` task
- Removed `bucket` from pluginDefaults

**08_gcp_taxi.yaml & 09_gcp_taxi_scheduled.yaml:**
- Removed `gcs_file` variable
- Replaced `upload_to_gcs` (GCS Upload) with `load_to_bq_staging` (BigQuery Load)
- Removed external table creation tasks (`bq_yellow_table_ext`, `bq_green_table_ext`)
- Modified temp table queries to select from `_staging` table instead of `_ext`
- Added explicit column casting to match final table schema
- Removed `bucket` from pluginDefaults

### BigQuery Load Task Configuration

```yaml
- id: load_to_bq_staging
  type: io.kestra.plugin.gcp.bigquery.Load
  from: "{{render(vars.data)}}"
  destinationTable: "{{kv('GCP_PROJECT_ID')}}.{{render(vars.table)}}_staging"
  format: CSV
  csvOptions:
    fieldDelimiter: ","
    skipLeadingRows: "1"
    allowJaggedRows: true
    allowQuotedNewLines: true
  writeDisposition: WRITE_TRUNCATE
  autodetect: true
```

---

## Running the GCP Flows

### Prerequisites

1. GCP Project with BigQuery API enabled
2. Service account with roles:
   - BigQuery Data Editor
   - BigQuery Job User
3. Service account key (JSON) stored in Kestra KV store as `GCP_CREDS`

### Execution Order

```
1. Run 06_gcp_kv       # Set GCP configuration (project, location, dataset)
2. Run 07_gcp_setup    # Create BigQuery dataset
3. Run 08_gcp_taxi     # Load taxi data (manual, select taxi/year/month)
4. Run 09_gcp_taxi_scheduled  # Or use scheduled version with backfill
```

### Setting Up GCP Credentials in Kestra

1. Navigate to Kestra UI -> Namespaces -> zoomcamp -> KV Store
2. Add key `GCP_CREDS` with your service account JSON (minified, single line)
3. Run flow 06_gcp_kv to set project ID, location, and dataset name

---

## Kestra Concepts

### Flow Structure

```yaml
id: flow_name
namespace: zoomcamp

inputs:
  - id: input_name
    type: STRING/SELECT/ARRAY
    defaults: default_value

variables:
  var_name: "{{inputs.input_name}}"

tasks:
  - id: task_id
    type: io.kestra.plugin.xxx
    # task configuration

pluginDefaults:
  - type: io.kestra.plugin.xxx
    values:
      # default values for all tasks of this type

triggers:
  - id: schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 9 1 * *"
```

### Common Task Types

| Task Type | Purpose |
| --------- | ------- |
| `io.kestra.plugin.core.log.Log` | Log messages |
| `io.kestra.plugin.core.http.Download` | Download files from URL |
| `io.kestra.plugin.scripts.python.Script` | Run Python scripts |
| `io.kestra.plugin.scripts.shell.Commands` | Run shell commands |
| `io.kestra.plugin.jdbc.postgresql.Queries` | Execute PostgreSQL queries |
| `io.kestra.plugin.jdbc.postgresql.CopyIn` | Bulk load CSV into PostgreSQL |
| `io.kestra.plugin.gcp.bigquery.Query` | Execute BigQuery SQL |
| `io.kestra.plugin.gcp.bigquery.Load` | Load data into BigQuery |
| `io.kestra.plugin.core.flow.If` | Conditional branching |
| `io.kestra.plugin.core.kv.Set` | Set key-value pairs |

### Templating

Kestra uses Pebble templating:

```yaml
# Access inputs
"{{inputs.taxi}}"

# Access variables
"{{render(vars.file)}}"

# Access outputs from previous tasks
"{{outputs.extract.outputFiles['file.csv']}}"

# Access KV store
"{{kv('GCP_PROJECT_ID')}}"

# Date formatting (in triggers)
"{{trigger.date | date('yyyy-MM')}}"
```

### Backfill

For scheduled flows, use backfill to run historical dates:

1. Go to flow -> Triggers tab
2. Click "Backfill" on a trigger
3. Select date range
4. Add label `backfill:true` for tracking

---

## Troubleshooting

### Kestra Not Starting

Check kestra_postgres is healthy:

```powershell
docker-compose logs kestra_postgres
```

### Flow Execution Fails

1. Check Logs tab in Kestra UI
2. Verify KV store values are set correctly
3. For GCP flows, verify service account permissions

### BigQuery Permission Errors

Ensure service account has:
- `roles/bigquery.dataEditor` - Create/modify tables
- `roles/bigquery.jobUser` - Run queries

### Docker Socket Issues (Windows)

Ensure Docker Desktop is running and WSL integration is enabled.

---

## Key Takeaways

1. **Workflow Orchestration** - Kestra provides declarative YAML-based workflow definitions
2. **Modularity** - Flows can be chained and reused with different inputs
3. **Scheduling** - Cron-based triggers with backfill support for historical data
4. **Plugin Ecosystem** - Native integrations for PostgreSQL, BigQuery, GCS, Python, etc.
5. **Flexibility** - When one approach doesn't work (GCS), alternatives exist (BigQuery Load)
