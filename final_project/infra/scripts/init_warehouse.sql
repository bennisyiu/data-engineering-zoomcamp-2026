-- Run on first init of warehouse Postgres (EC2 / Docker)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS raw_streaming;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

-- Stream landing zone (PyFlink Kafka → JDBC). Batch CSV pipeline unchanged; dbt v2 could add staging from here.
CREATE TABLE IF NOT EXISTS raw_streaming.stream_policy_events (
  id BIGSERIAL PRIMARY KEY,
  policy_number TEXT,
  event_type TEXT,
  payload TEXT,
  event_time TIMESTAMPTZ NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stream_policy_events_event_time
  ON raw_streaming.stream_policy_events (event_time DESC);

-- Read-only reviewer user (for course reviewers to explore the warehouse)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reviewer') THEN
    CREATE ROLE reviewer WITH LOGIN PASSWORD 'reviewer_readonly';
  END IF;
END$$;

GRANT CONNECT ON DATABASE insurance_dwh TO reviewer;
GRANT USAGE ON SCHEMA raw, raw_streaming, staging, intermediate, marts TO reviewer;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, raw_streaming, staging, intermediate, marts TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_streaming GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT SELECT ON TABLES TO reviewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO reviewer;
