"""
Daily ingestion: load policy, invoice, claim from local data/ or S3 into raw schema.
Mimics a real pipeline: full refresh of raw tables per run, with optional S3 source.
"""
import os
import io
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def _configure_postgres_env() -> None:
    """Load project .env without clobbering compose-provided vars; fix Docker/Airflow + localhost."""
    load_dotenv(override=False)
    # .env often uses localhost for host-side clients; in Compose the DWH is service `warehouse`.
    in_managed_runtime = bool(os.environ.get("AIRFLOW_HOME")) or os.path.exists("/.dockerenv")
    if in_managed_runtime:
        h = (os.environ.get("POSTGRES_HOST") or "").strip().lower()
        if h in ("", "localhost", "127.0.0.1"):
            os.environ["POSTGRES_HOST"] = "warehouse"
            os.environ.setdefault("POSTGRES_PORT", "5432")


def _db_settings():
    """Read connection settings after env configuration (not at stale import time)."""
    _configure_postgres_env()
    return (
        os.getenv("POSTGRES_HOST"),
        os.getenv("POSTGRES_PORT"),
        os.getenv("POSTGRES_USER"),
        os.getenv("POSTGRES_PASSWORD"),
        os.getenv("POSTGRES_DB"),
    )

# Data source: S3 prefix (e.g. raw/) or local data/ directory
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_RAW_PREFIX", "raw")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CSV_TO_TABLE = {
    "policy.csv": "raw_policy",
    "invoice.csv": "raw_invoice",
    "claim.csv": "raw_claim",
}


def get_engine():
    # URL-encode user/password so @, #, $, % in password don't break the DSN
    db_host, db_port, db_user, db_password, db_name = _db_settings()
    user = quote_plus(db_user or "")
    password = quote_plus(db_password or "")
    url = f"postgresql://{user}:{password}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)


def load_csv_from_s3(s3_client, bucket: str, key: str) -> pd.DataFrame:
    """Read a CSV from S3 into a DataFrame."""
    resp = s3_client.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(resp["Body"].read()), dtype=str)


def load_csv_local(filepath: str) -> pd.DataFrame:
    """Read a CSV from local path into a DataFrame."""
    return pd.read_csv(filepath, dtype=str)


def load_csv_to_raw(engine, df: pd.DataFrame, table_name: str):
    """Full refresh: drop with CASCADE (removes dependent dbt views — they get
    recreated by dbt_run in the next DAG task), then load fresh."""
    df = df.copy()
    df["_loaded_at"] = pd.Timestamp.utcnow()
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS raw.{table_name} CASCADE"))
    df.to_sql(name=table_name, con=engine, schema="raw",
              if_exists="replace", index=False)
    print(f"  -> raw.{table_name} ({len(df)} rows)")


def main():
    engine = get_engine()
    _h, _p, _, _, _db = _db_settings()
    print(f"Connected to {_db} at {_h}:{_p}")
    print("Loading CSVs into raw schema (full refresh)...")

    if S3_BUCKET:
        import boto3
        from botocore.exceptions import ClientError
        s3 = boto3.client("s3")
        prefix = f"{S3_PREFIX.rstrip('/')}/"
        for csv_file, table_name in CSV_TO_TABLE.items():
            key = f"{prefix}{csv_file}"
            try:
                df = load_csv_from_s3(s3, S3_BUCKET, key)
                load_csv_to_raw(engine, df, table_name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    print(f"  Skipped {key} (not found in S3)")
                else:
                    raise
    else:
        for csv_file, table_name in CSV_TO_TABLE.items():
            filepath = os.path.join(DATA_DIR, csv_file)
            if not os.path.isfile(filepath):
                print(f"  Skipped {csv_file} (not found in data/)")
                continue
            df = load_csv_local(filepath)
            load_csv_to_raw(engine, df, table_name)

    print("Done!")


if __name__ == "__main__":
    main()
