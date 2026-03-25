# PySpark with Docker

Docker eliminates the Java/Hadoop/environment variable pain entirely. The container ships with everything pre-configured — no need to install Java, set `JAVA_HOME`, `HADOOP_HOME`, or wrestle with PATH variables on your host machine.

## Why Docker for PySpark?

- **Zero local dependency management** — Java, Hadoop, Spark all live inside the container
- **Reproducible environment** — same setup on any machine with Docker installed
- **Isolated from host** — no conflicts with other Java versions or system packages
- **Version-controlled** — pin exact Spark/Java versions in your Dockerfile

---

## Project Structure

Based on your current Zoomcamp directory layout:

```
data-engineering-zoomcamp-2026/
├── module_6_batch_processing/
│   ├── pyspark-docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.txt
│   │   ├── data/              # Downloaded datasets (parquet, csv)
│   │   └── app/
│   │       └── homework.py
│   └── requirements.txt
├── venv/
├── venv_office/
└── README.md
```

---

## Step 1: Create the Dockerfile

```dockerfile
# Version: v2.0 - Custom PySpark Dockerfile (updated for homework)
FROM apache/spark-py:3.5.1

USER root

# Install wget for downloading datasets
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /opt/spark/requirements.txt
RUN pip install --no-cache-dir -r /opt/spark/requirements.txt

# Set working directory
WORKDIR /opt/spark/work-dir

USER spark
```

> 💡 `apache/spark-py:3.5.1` comes with Java 17, Hadoop 3, and PySpark pre-installed. No environment variables needed.

---

## Step 2: Create requirements.txt

```txt
# Version: v1.0 - PySpark dependencies
pyspark==3.5.1
pandas
pyarrow
```

---

## Step 3: Create docker-compose.yml

```yaml
# Version: v2.0 - PySpark Docker Compose (updated for homework)
version: "3.8"
services:
  pyspark:
    build: .
    container_name: pyspark-dev
    volumes:
      - ./app:/opt/spark/work-dir
      - ./data:/opt/spark/data # Mount data directory for datasets
    ports:
      - "4040:4040" # Spark UI
    stdin_open: true
    tty: true
    command: /bin/bash
```

> 📁 The `volumes` mount maps your local `./app` folder into the container. Edit files locally, run them inside the container.

---

## Step 4: Download Homework Datasets

The homework uses Yellow Taxi November 2025 data and zone lookup CSV.

```powershell
# Version: v2.0 - Download homework datasets (PowerShell)
New-Item -ItemType Directory -Force -Path data
Invoke-WebRequest -Uri "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-11.parquet" -OutFile "data\yellow_tripdata_2025-11.parquet"
Invoke-WebRequest -Uri "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv" -OutFile "data\taxi_zone_lookup.csv"
```

> 📦 Download these **before** building the container. The `data/` folder is mounted into the container at `/opt/spark/data`.

---

## Step 5: Build and Run

### Build the image

```bash
# Version: v2.0 - Build the Docker image
cd module_6_batch_processing/pyspark-docker
docker compose build
```

### Start the container (interactive shell)

```bash
# Version: v2.0 - Start interactive container
docker compose run --rm pyspark
```

---

## Step 6: Verify Inside the Container

### Test PySpark shell

```bash
# Version: v1.0 - Launch interactive PySpark shell
pyspark
```

### Run a script

```bash
# Version: v1.0 - Run a PySpark script
spark-submit /opt/spark/work-dir/homework.py
```

### Quick verification script

```python
# Version: v1.0 - verify_pyspark.py
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("local[*]") \
    .appName("Docker PySpark Test") \
    .getOrCreate()

df = spark.createDataFrame([
    ("Java", "handled by Docker"),
    ("Hadoop", "handled by Docker"),
    ("Spark", "handled by Docker"),
], ["dependency", "status"])

df.show()
print(f"Spark version: {spark.version}")
print(f"Java home: {spark.sparkContext._jvm.System.getProperty('java.home')}")

spark.stop()
```

---

## What This Gives You

| Feature               | Detail                                                     |
| --------------------- | ---------------------------------------------------------- |
| Java, Hadoop, Spark   | Pre-installed and configured inside the container          |
| Environment variables | None required on your host machine                         |
| Local editing         | `./app` folder is mounted — edit locally, run in container |
| Port 4040             | Exposed for Spark UI monitoring                            |
| Reproducibility       | Works on any machine with Docker installed                 |

---

## Homework Reference

Source: [Module 6 Homework](https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/cohorts/2026/06-batch/homework.md)

Submission form: [HW6 Submission](https://courses.datatalks.club/de-zoomcamp-2026/homework/hw6)

### Homework Questions Overview

| Q#  | Topic                 | Key Task                                                     |
| --- | --------------------- | ------------------------------------------------------------ |
| Q1  | Install Spark         | Create local Spark session, check `spark.version`            |
| Q2  | Yellow Nov 2025       | Read parquet → repartition to 4 → save → check avg file size |
| Q3  | Count records         | Count trips starting on Nov 15                               |
| Q4  | Longest trip          | Calculate longest trip duration in hours                     |
| Q5  | Spark UI              | Identify the Spark UI port (4040)                            |
| Q6  | Least frequent pickup | Join with zone lookup → find least frequent pickup zone      |

### Data Paths Inside Container

| Dataset                | Container Path                                    |
| ---------------------- | ------------------------------------------------- |
| Yellow Taxi Nov 2025   | `/opt/spark/data/yellow_tripdata_2025-11.parquet` |
| Taxi Zone Lookup       | `/opt/spark/data/taxi_zone_lookup.csv`            |
| Output (repartitioned) | `/opt/spark/data/output/yellow_nov_2025/`         |
