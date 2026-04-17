-- Idempotent migration: stream landing zone for PyFlink (and future dbt staging).
-- Run on existing warehouses where init_warehouse.sql already ran once:
--   psql -h <host> -U <user> -d insurance_dwh -f infra/scripts/add_raw_streaming.sql

CREATE SCHEMA IF NOT EXISTS raw_streaming;

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

DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reviewer') THEN
    GRANT USAGE ON SCHEMA raw_streaming TO reviewer;
    GRANT SELECT ON ALL TABLES IN SCHEMA raw_streaming TO reviewer;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw_streaming GRANT SELECT ON TABLES TO reviewer;
  END IF;
END$$;
