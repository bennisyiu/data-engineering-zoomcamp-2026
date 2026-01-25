## Module 1 - Docker & Terraform

Remarks: I am more familiar with the Windows PowerShell and commands, as well as the usual Python VENV with pip & requirements.txt.

### Directory setup:

| data-engineering-zoomcamp-2026
|**| module_1_docker_terraform
|\_\_**|ny_taxi_postgres_data
|\_**\_ Dockerfile
|\_\_** ingest_data.py
|\_**\_ output_day_10.parquet
|\_\_** requirements.txt
|**.gitignore
|** README.md

### Dependencies | requirements.txt

```
pandas
pyarrow
pgcli
jupyter
sqlalchemy
psycopg2-binary
tqdm

```

---

## Initial Docker Commands

1. When Dockerfile is ready, build image:

docker build -t test:pandas .

2. Run PostgreSQL (basic, no network):

```
docker run -it `
    -e POSTGRES_USER="root"`
    -e POSTGRES_PASSWORD="root" `
    -e POSTGRES_DB="ny_taxi"`
    -v C:\Users\Bennis\OneDrive\Personal_OneDrive\Coding\data-engineering-zoomcamp-2026\module_1_docker_terraform\ny_taxi_postgres_data:/var/lib/postgresql/data `
    -p 5432:5432`
    postgres:13

```

3. Connect with pgcli (in new terminal):

pgcli -h localhost -p 5432 -u root -d ny_taxi

4. Basic SQL commands:

-- List tables
\dt

-- Create test table
CREATE TABLE test (id INTEGER, name VARCHAR(50));

-- Insert data
INSERT INTO test VALUES (1, 'Hello Docker');

-- Query data
SELECT \* FROM test;

-- Exit
\q

5. Convert Jupyter notebook to Python script:

jupyter nbconvert --to script notebook.ipynb
mv notebook.py ingest_data.py

6. Run data ingestion script:

```
python ingest_data.py `
    --pg-user=root`
    --pg-pass=root `
    --pg-host=localhost`
    --pg-port=5432 `
    --pg-db=ny_taxi`
    --target-table=yellow_taxi_trips
```

---

## Docker Networking Setup (Production Pattern)

### Step 1: Create Docker Network

`docker network create pg-network`

Verify:
`docker network ls`

### Step 2: Run PostgreSQL on Network

Stop any existing container first, then:

```
docker run -it `
    -e POSTGRES_USER="root"`
    -e POSTGRES_PASSWORD="root" `
    -e POSTGRES_DB="ny_taxi"`
    -v ny_taxi_postgres_data:/var/lib/postgresql/data `
    -p 5432:5432`
    --network=pg-network `
    --name pgdatabase`
    postgres:13
```

Keep this terminal running.

### Step 3: Run pgAdmin on Network

Open new terminal:

```
docker run -it `
    -e PGADMIN_DEFAULT_EMAIL="admin@admin.com"`
    -e PGADMIN_DEFAULT_PASSWORD="root" `
    -v pgadmin_data:/var/lib/pgadmin`
    -p 8085:80 `
    --network=pg-network`
    --name pgadmin `
    dpage/pgadmin4
```

Keep this terminal running.

### Step 4: Connect pgAdmin to PostgreSQL

1. Open browser: http://localhost:8085
2. Login: admin@admin.com / root
3. Register Server:
   - General tab: Name = Local Docker
   - Connection tab:
     - Host: pgdatabase (container name)
     - Port: 5432
     - Database: ny_taxi
     - Username: root
     - Password: root

---

## Connection Reference

| Component  | From Host Machine | From Container  |
| ---------- | ----------------- | --------------- |
| PostgreSQL | localhost:5432    | pgdatabase:5432 |
| pgAdmin    | localhost:8085    | N/A             |

Key: Use localhost from host machine (Python, pgcli). Use container name from containers (pgAdmin).

---

## Managing Docker Resources

### Stop Containers

Press Ctrl+C in running terminals

### Remove Containers

`docker rm pgdatabase`
`docker rm pgadmin`

Force remove:
`docker rm -f pgdatabase`
`docker rm -f pgadmin`

### Remove Network

`docker network rm pg-network`

### List Resources

`docker ps` # Running containers
`docker ps -a` # All containers
`docker volume ls` # Volumes
`docker network ls` # Networks

### Remove Volumes (deletes data!)

`docker volume rm ny_taxi_postgres_data`
`docker volume rm pgadmin_data`

---

## Troubleshooting

### Port Conflict

If port already in use, change host port:

`-p 5433:5432 # PostgreSQL`
`-p 8086:80 # pgAdmin`

### Container Name Conflict

`docker rm -f pgdatabase`
`docker rm -f pgadmin`

### Network Connection Issues

Verify containers on same network:

`docker inspect pgdatabase | Select-String "pg-network"`
`docker inspect pgadmin | Select-String "pg-network"`

---

## Dockerizing the Ingestion Script

### Create Dockerfile

Create a file named `Dockerfile` in your project directory:

```
FROM python:3.13-slim
WORKDIR /app

# Copy requirements file

COPY requirements.txt .

# Install dependencies

RUN pip install --no-cache-dir -r requirements.txt

# Copy ingestion script

COPY ingest_data.py .

# Set entrypoint

ENTRYPOINT ["python", "ingest_data.py"]
```

### Build the Docker Image

Navigate to your project directory (where Dockerfile and ingest_data.py are):
`cd module_1_docker_terraform`
`docker build -t taxi_ingest:v001 .`

### Run the Containerized Ingestion

Run the container on the same network as PostgreSQL:

```
docker run -it `
    --network=pg-network taxi_ingest:v001 `
    --pg-user=root `
    --pg-pass=root `
    --pg-host=pgdatabase `
    --pg-port=5432 `
    --pg-db=ny_taxi `
    --target-table=yellow_taxi_trips`
```

### Important Notes

- Network: Provide --network=pg-network so container can find PostgreSQL
- Host: Use pgdatabase (container name) not localhost since running in container
- Table drop: Script will replace pre-existing table automatically
- One-time run: Container runs once and exits when ingestion completes

### Verify Data

In pgcli or pgAdmin:
SELECT COUNT(_) FROM yellow_taxi_trips;
SELECT _ FROM yellow_taxi_trips LIMIT 10;
