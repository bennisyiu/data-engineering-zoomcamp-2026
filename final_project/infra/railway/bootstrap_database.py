"""Initialize Railway PostgreSQL schemas and least-privilege application roles."""

from __future__ import annotations

import os

import psycopg2
from psycopg2 import sql


SCHEMAS = ("raw", "raw_streaming", "staging", "intermediate", "marts")


def ensure_login_role(cursor, role: str, password: str) -> None:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    statement = "ALTER ROLE {} LOGIN PASSWORD %s" if cursor.fetchone() else "CREATE ROLE {} LOGIN PASSWORD %s"
    cursor.execute(sql.SQL(statement).format(sql.Identifier(role)), (password,))


def main() -> None:
    admin_url = os.getenv("ADMIN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not admin_url:
        raise RuntimeError("Set ADMIN_DATABASE_URL or DATABASE_URL to initialize PostgreSQL")

    pipeline_user = os.getenv("PIPELINE_DB_USER", "pipeline_writer")
    pipeline_password = os.getenv("PIPELINE_DB_PASSWORD")
    reader_user = os.getenv("STREAMLIT_DB_USER", "streamlit_reader")
    reader_password = os.getenv("STREAMLIT_DB_PASSWORD")
    airflow_user = os.getenv("AIRFLOW_DB_USER", "airflow_user")
    airflow_password = os.getenv("AIRFLOW_DB_PASSWORD")
    airflow_database = os.getenv("AIRFLOW_DB_NAME", "airflow")

    connection = psycopg2.connect(admin_url)
    connection.autocommit = True
    try:
        database = connection.get_dsn_parameters()["dbname"]
        with connection.cursor() as cursor:
            for schema in SCHEMAS:
                cursor.execute(
                    sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
                )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_streaming.stream_policy_events (
                    id BIGSERIAL PRIMARY KEY,
                    policy_number TEXT,
                    event_type TEXT,
                    payload TEXT,
                    event_time TIMESTAMPTZ NOT NULL,
                    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stream_policy_events_event_time
                ON raw_streaming.stream_policy_events (event_time DESC)
                """
            )

            if pipeline_password:
                ensure_login_role(cursor, pipeline_user, pipeline_password)
                cursor.execute(
                    sql.SQL("GRANT CONNECT, CREATE ON DATABASE {} TO {}").format(
                        sql.Identifier(database), sql.Identifier(pipeline_user)
                    )
                )
                for schema in SCHEMAS:
                    cursor.execute(
                        sql.SQL("GRANT USAGE, CREATE ON SCHEMA {} TO {}").format(
                            sql.Identifier(schema), sql.Identifier(pipeline_user)
                        )
                    )
                    cursor.execute(
                        sql.SQL(
                            "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {} TO {}"
                        ).format(sql.Identifier(schema), sql.Identifier(pipeline_user))
                    )
                    cursor.execute(
                        sql.SQL(
                            "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {} TO {}"
                        ).format(sql.Identifier(schema), sql.Identifier(pipeline_user))
                    )

            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'marts_reader') THEN
                        CREATE ROLE marts_reader NOLOGIN;
                    END IF;
                END
                $$;
                """
            )
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO marts_reader").format(
                    sql.Identifier(database)
                )
            )
            cursor.execute("GRANT USAGE ON SCHEMA marts TO marts_reader")
            cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA marts TO marts_reader")
            cursor.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA marts "
                "GRANT SELECT ON TABLES TO marts_reader"
            )
            if pipeline_password:
                cursor.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA marts "
                        "GRANT SELECT ON TABLES TO marts_reader"
                    ).format(sql.Identifier(pipeline_user))
                )

            if reader_password:
                ensure_login_role(cursor, reader_user, reader_password)
                cursor.execute(
                    sql.SQL("GRANT marts_reader TO {}").format(sql.Identifier(reader_user))
                )
                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} SET default_transaction_read_only TO on"
                    ).format(sql.Identifier(reader_user))
                )
                cursor.execute(
                    sql.SQL("ALTER ROLE {} SET statement_timeout TO '15s'").format(
                        sql.Identifier(reader_user)
                    )
                )
                cursor.execute(
                    sql.SQL("ALTER ROLE {} CONNECTION LIMIT 5").format(
                        sql.Identifier(reader_user)
                    )
                )

            if airflow_password:
                ensure_login_role(cursor, airflow_user, airflow_password)
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (airflow_database,),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            sql.Identifier(airflow_database),
                            sql.Identifier(airflow_user),
                        )
                    )
                cursor.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(airflow_database),
                        sql.Identifier(airflow_user),
                    )
                )
    finally:
        connection.close()

    print("Railway database schemas and roles initialized.")


if __name__ == "__main__":
    main()
