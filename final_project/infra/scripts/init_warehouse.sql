-- Run on first init of warehouse Postgres (EC2 / Docker)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

-- Read-only reviewer user (for interviewers to run Q1 SQL and explore the warehouse)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reviewer') THEN
    CREATE ROLE reviewer WITH LOGIN PASSWORD 'reviewer_readonly';
  END IF;
END$$;

GRANT CONNECT ON DATABASE insurance_dwh TO reviewer;
GRANT USAGE ON SCHEMA raw, staging, intermediate, marts TO reviewer;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, staging, intermediate, marts TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO reviewer;
