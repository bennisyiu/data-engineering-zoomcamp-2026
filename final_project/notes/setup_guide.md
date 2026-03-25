# Setup Guide (Personal Reference)

> Gitignored — personal reference only, not part of the submission.

---

## Build Order

The build is ordered local-first, then AWS, so that iteration can be done without incurring cloud cost.

| Phase | Content | Rationale |
|-------|---------|-----------|
| **Phase 1** | Local PostgreSQL + load data | Data is required before SQL and dbt |
| **Phase 2** | S3 bucket | Data lake and extract script validation |
| **Phase 3** | SQL analytics | Executed after EDA |
| **Phase 4** | dbt transformations | Transformation layer |
| **Phase 5** | Airflow + Docker | Full pipeline run locally |
| **Phase 6** | Tableau dashboard | Built after marts are ready |
| **Phase 7** | EC2 deployment | Deployed only after local is working |

---

## Phase 1: Local PostgreSQL Setup

### 1.1 Check Postgres

```bash
psql --version
```

PostgreSQL 15.x is used; the Postgres service must be running (e.g. Windows Services).

### 1.2 Create the database

```sql
CREATE DATABASE insurance_dwh;
```

The database name `insurance_dwh` is used; any name is valid provided scripts and dbt are configured for it.

### 1.3 Create the schemas

In `insurance_dwh`:

```sql
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;
```

### 1.4 .env file

A `.env` file is created in the project root (gitignored) with:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<mine>
POSTGRES_DB=insurance_dwh

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-southeast-1
S3_BUCKET_NAME=
```

Region `ap-southeast-1` (Singapore) is used; alternatives are `ap-east-1` (Hong Kong) and `ap-northeast-1` (Tokyo).

### 1.5 Load CSVs into raw

The extract_load script reads the three CSVs from `data/`, creates tables in `raw`, and loads data as-is; transformation is handled by dbt.

### 1.6 Explore in PgAdmin

After load, row counts, column types, nulls, `policy_number` relationships, and multi-policy users (for new vs returning analysis) are reviewed; these findings inform the SQL and dbt design.

---

## Phase 2: S3 Bucket Setup

### 2.1 AWS CLI

```bash
aws sts get-caller-identity
```

If the command fails, `aws configure` is run with the appropriate credentials.

### 2.2 Bucket name

S3 bucket names are globally unique, lowercase, no underscores, 3–63 characters (e.g. `bennis-insurance-dwh-data-lake`).

### 2.3 Create bucket

```bash
aws s3 mb s3://<bucket-name> --region ap-southeast-1
```

### 2.4 raw/ prefix

```bash
aws s3api put-object --bucket <bucket-name> --key raw/
```

### 2.5 Upload CSVs

```bash
aws s3 cp data/policy.csv s3://<bucket-name>/raw/policy.csv
aws s3 cp data/invoice.csv s3://<bucket-name>/raw/invoice.csv
aws s3 cp data/claim.csv s3://<bucket-name>/raw/claim.csv
aws s3 ls s3://<bucket-name>/raw/
```

### 2.6 .env

`S3_BUCKET_NAME` and `AWS_REGION` are set in `.env`.

### 2.7 Block public access

```bash
aws s3api put-public-access-block --bucket <bucket-name> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Phase 3–6: Development

Phases 3–6 are executed in order: SQL after EDA, dbt after SQL, Airflow + Docker after dbt, Tableau after marts.

---

## Phase 7: EC2 Deployment

EC2 deployment is performed only after the local pipeline is working.

### 7.1 Instance type

Instance type `t3.small` (2 vCPU, 2GB) is used for headroom; `t3.micro` is free tier but tight for Airflow + Postgres + dbt.

### 7.2 Key pair

```bash
aws ec2 create-key-pair --key-name insurance-dwh-key --query 'KeyMaterial' --output text > insurance-dwh-key.pem
```

Permissions are set via `chmod 400` (Linux/Mac) or icacls on Windows. `*.pem` is in .gitignore and must not be committed.

### 7.3 Security group

A security group is created; ingress is added for SSH (restricted IP), 8080 (Airflow), and 5432 (PostgreSQL for reviewer access). The host IP is obtained via `curl ifconfig.me`.

### 7.4 Launch instance

```bash
aws ec2 run-instances --image-id ami-0c55b159cbfafe1f0 --instance-type t3.small --key-name insurance-dwh-key --security-groups insurance-dwh-sg --count 1 --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=insurance-dwh}]'
```

AMI IDs are region-specific; the example is Amazon Linux 2. For Ubuntu, the current AMI for the chosen region is used.

### 7.5 SSH

```bash
ssh -i insurance-dwh-key.pem ec2-user@<EC2_PUBLIC_IP>
```

Use `ubuntu@` if the AMI is Ubuntu.

### 7.6 Docker on EC2

On Amazon Linux 2: Docker is installed via yum, the service is started, the user is added to the docker group, and Docker Compose is installed from GitHub; then log out and back in for group changes.

### 7.7 Deploy

The repo is cloned on the instance, `infra/.env.example` is copied to `.env` and populated, then `cd infra` and `docker compose up -d` are run.

### 7.8 Check

Airflow is available at `http://<EC2_PUBLIC_IP>:8082`. The DAG is triggered to verify the pipeline.

### 7.9 Cost

The instance is stopped when not in use (`aws ec2 stop-instances`) and started when needed. After submission, the instance can be terminated and the S3 bucket removed if desired.

---

## Checklist

Postgres + schemas + .env; data loaded and explored; S3 + CSVs; SQL and dbt; Airflow locally; Tableau; EC2 deploy; README URLs; collaborator; submission.

---

## Troubleshooting Notes

(Personal notes for issues encountered.)

