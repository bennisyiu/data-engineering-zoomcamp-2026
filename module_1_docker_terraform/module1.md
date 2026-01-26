## Module 1 - Docker & Terraform

Remarks: I am more familiar with the Windows PowerShell and commands, as well as the usual Python VENV with pip & requirements.txt.

### Directory setup:

```
| data-engineering-zoomcamp-2026
|\_| module_1_docker_terraform
  |\_| ny_taxi_postgres_data
  |\_  Dockerfile
  |\_  docker-compose.yaml
  |\_  homework.sql
  |\_  ingest_data.py
  |\_  module1.md
  |\_  output_day_10.parquet
  |\_  requirements.txt
|\_  .gitignore
|\_  README.md
```

### Dependencies | requirements.txt

```
pandas
pyarrow
pgcli
jupyter
sqlalchemy
psycopg2-binary
tqdm
click
```

---

## Docker Basics

### Initial Docker Commands

1. When Dockerfile is ready, build image:

`docker build -t test:pandas .`

2. Run PostgreSQL (basic, no network):

```
docker run -it `
    -e POSTGRES_USER="root" `
    -e POSTGRES_PASSWORD="root" `
    -e POSTGRES_DB="ny_taxi" `
    -v C:\Users\Bennis\OneDrive\Personal_OneDrive\Coding\data-engineering-zoomcamp-2026\module_1_docker_terraform\ny_taxi_postgres_data:/var/lib/postgresql/data `
    -p 5432:5432 `
    postgres:13
```

3. Connect with pgcli (in new terminal):

`pgcli -h localhost -p 5432 -u root -d ny_taxi`

4. Basic SQL commands:

```
-- List tables
\dt

-- Create test table
CREATE TABLE test (id INTEGER, name VARCHAR(50));

-- Insert data
INSERT INTO test VALUES (1, 'Hello Docker');

-- Query data
SELECT * FROM test;

-- Exit
\q
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
    -e POSTGRES_USER="root" `
    -e POSTGRES_PASSWORD="root" `
    -e POSTGRES_DB="ny_taxi" `
    -v ny_taxi_postgres_data:/var/lib/postgresql/data `
    -p 5432:5432 `
    --network=pg-network `
    --name pgdatabase `
    postgres:13
```

Keep this terminal running.

### Step 3: Run pgAdmin on Network

Open new terminal:

```
docker run -it `
    -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" `
    -e PGADMIN_DEFAULT_PASSWORD="root" `
    -v pgadmin_data:/var/lib/pgadmin `
    -p 8085:80 `
    --network=pg-network `
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

## Dockerized Ingestion Pipeline

### Final Dockerfile (v003)

```
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest_data.py ./

ENTRYPOINT ["python", "ingest_data.py"]
```

### Build the Docker Image

`cd module_1_docker_terraform`
`docker build -t taxi_ingest:v003 .`

### Run Ingestion with Dataset Selection

Load all datasets (yellow taxi, green taxi, zones):

`docker run -it --network=pg-network taxi_ingest:v003 --pg-user=root --pg-pass=root --pg-host=pgdatabase --pg-port=5432 --pg-db=ny_taxi --dataset=all`

Load individual datasets:

```
--dataset=yellow  # Yellow taxi only
--dataset=green   # Green taxi only
--dataset=zones   # Zones only
```

---

## Docker Compose Setup

### docker-compose.yaml

```
services:
  pgdatabase:
    image: postgres:13
    environment:
      POSTGRES_USER: "root"
      POSTGRES_PASSWORD: "root"
      POSTGRES_DB: "ny_taxi"
    volumes:
      - "ny_taxi_postgres_data:/var/lib/postgresql/data"
    ports:
      - "5432:5432"

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: "admin@admin.com"
      PGADMIN_DEFAULT_PASSWORD: "root"
    volumes:
      - "pgadmin_data:/var/lib/pgadmin"
    ports:
      - "8085:80"

volumes:
  ny_taxi_postgres_data:
  pgadmin_data:
```

### Docker Compose Commands

# Start services in background

`docker-compose up -d`

# View running services

`docker-compose ps`

# View logs

`docker-compose logs`
`docker-compose logs -f` # Follow logs

# Stop services

`docker-compose down`

# Stop and remove volumes

`docker-compose down -v`

### Run Ingestion with Docker Compose Network

`docker run -it --network=module_1_docker_terraform_default taxi_ingest:v003 --pg-user=root --pg-pass=root --pg-host=pgdatabase --pg-port=5432 --pg-db=ny_taxi --dataset=all`

---

## Managing Docker Resources

### Stop Containers

Press Ctrl+C in running terminals, or:

`docker stop pgdatabase pgadmin`

### Remove Containers

`docker rm pgdatabase`
`docker rm pgadmin`

Force remove:
`docker rm -f pgdatabase pgadmin`

### Remove Network

`docker network rm pg-network`

### List Resources

```
docker ps              # Running containers
docker ps -a           # All containers
docker volume ls       # Volumes
docker network ls      # Networks
docker images          # Images
```

### Remove Volumes (deletes data!)

`docker volume rm ny_taxi_postgres_data`
`docker volume rm pgadmin_data`

### Clean Up Unused Resources

# Remove stopped containers

`docker container prune`

# Remove unused images

`docker image prune -a`

# Remove unused volumes

`docker volume prune`

# Remove everything unused

`docker system prune -a`

---

## Troubleshooting

### Port Conflict

If port already in use, change host port:

```
-p 5433:5432  # PostgreSQL
-p 8086:80    # pgAdmin
```

### Container Name Conflict

```
docker rm -f pgdatabase
docker rm -f pgadmin
```

### Network Connection Issues

Verify containers on same network:

```
docker inspect pgdatabase | Select-String "pg-network"
docker inspect pgadmin | Select-String "pg-network"
```

### pgAdmin Connection Lost

Check container status:

`docker ps`

Restart container:
`docker start pgadmin`

Hard refresh browser: Ctrl + Shift + R

---

## Key Concepts

### Images vs Containers

- Image: Template/blueprint (like a class)
- Container: Running instance (like an object)
- Multiple containers can run from one image

### Volumes

- Persist data outside containers
- Survive container deletion
- Named volumes vs bind mounts

### Networks

- Allow container-to-container communication
- Use service/container names as hostnames
- Docker Compose creates default network automatically

### Docker Compose Benefits

- Single file defines entire stack
- Service names automatically resolve for networking
- One command starts/stops everything
- Version control friendly
- Repeatable deployments
