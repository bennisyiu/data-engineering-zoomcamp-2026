"""
Load policy, invoice, and claim data into the raw schema.

The source can be local data/, AWS S3, or any S3-compatible service such as a
Railway Storage Bucket. Raw refreshes use a staging table plus a transactional
TRUNCATE/INSERT so downstream dbt views never observe a partially loaded table.
"""
import os
import io
import re
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DATABASE_URL = os.getenv("DATABASE_URL")

# AWS names remain supported; Railway injects the shorter bucket variable names.
S3_BUCKET = os.getenv("S3_BUCKET_NAME") or os.getenv("BUCKET")
S3_PREFIX = os.getenv("S3_RAW_PREFIX", "raw")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL") or os.getenv("ENDPOINT")
S3_REGION = os.getenv("AWS_REGION") or os.getenv("REGION")
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("ACCESS_KEY_ID")
S3_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("SECRET_ACCESS_KEY")
DATA_DIR = REPO_ROOT / "data"

CSV_TO_TABLE = {
    "policy.csv": "raw_policy",
    "invoice.csv": "raw_invoice",
    "claim.csv": "raw_claim",
}


def get_engine():
    if DATABASE_URL:
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})

    if not all((DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)):
        raise ValueError(
            "Set DATABASE_URL or POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, "
            "POSTGRES_PASSWORD, and POSTGRES_DB"
        )
    # URL-encode user/password so @, #, $, % in password don't break the DSN
    user = quote_plus(DB_USER or "")
    password = quote_plus(DB_PASSWORD or "")
    url = f"postgresql://{user}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})


def get_s3_client():
    import boto3

    kwargs = {}
    if S3_ENDPOINT:
        kwargs["endpoint_url"] = S3_ENDPOINT
    if S3_REGION:
        kwargs["region_name"] = S3_REGION
    if S3_ACCESS_KEY:
        kwargs["aws_access_key_id"] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        kwargs["aws_secret_access_key"] = S3_SECRET_KEY
    return boto3.client("s3", **kwargs)


def load_csv_from_s3(s3_client, bucket: str, key: str) -> pd.DataFrame:
    """Read a CSV from S3 into a DataFrame."""
    resp = s3_client.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(io.BytesIO(resp["Body"].read()), dtype=str)


def load_csv_local(filepath: str) -> pd.DataFrame:
    """Read a CSV from local path into a DataFrame."""
    return pd.read_csv(filepath, dtype=str)


def quote_identifier(value: str) -> str:
    """Quote a controlled SQL identifier after rejecting unexpected characters."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return f'"{value}"'


def load_csv_to_raw(engine, df: pd.DataFrame, table_name: str):
    """Atomically refresh a raw table while preserving dependent dbt objects."""
    df = df.copy()
    df["_loaded_at"] = pd.Timestamp.utcnow()
    temp_name = f"_load_{table_name}_{uuid4().hex[:10]}"
    df.to_sql(name=temp_name, con=engine, schema="raw", if_exists="fail", index=False)

    inspector = inspect(engine)
    incoming_columns = list(df.columns)
    target_exists = inspector.has_table(table_name, schema="raw")
    target = f"raw.{quote_identifier(table_name)}"
    temp = f"raw.{quote_identifier(temp_name)}"

    try:
        with engine.begin() as conn:
            if not target_exists:
                conn.execute(
                    text(
                        f"ALTER TABLE {temp} "
                        f"RENAME TO {quote_identifier(table_name)}"
                    )
                )
            else:
                existing_columns = [
                    column["name"]
                    for column in inspector.get_columns(table_name, schema="raw")
                ]
                if existing_columns != incoming_columns:
                    raise ValueError(
                        f"Column mismatch for raw.{table_name}: "
                        f"existing={existing_columns}, incoming={incoming_columns}"
                    )
                columns = ", ".join(quote_identifier(column) for column in incoming_columns)
                conn.execute(text(f"LOCK TABLE {target} IN ACCESS EXCLUSIVE MODE"))
                conn.execute(text(f"TRUNCATE TABLE {target}"))
                conn.execute(
                    text(
                        f"INSERT INTO {target} ({columns}) "
                        f"SELECT {columns} FROM {temp}"
                    )
                )
                conn.execute(text(f"DROP TABLE {temp}"))
    except Exception:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {temp}"))
        raise

    print(f"  -> raw.{table_name} ({len(df)} rows)")


def main():
    engine = get_engine()
    print(f"Connected to {DB_NAME} at {DB_HOST}:{DB_PORT}")
    print("Loading CSVs into raw schema (full refresh)...")

    if S3_BUCKET:
        from botocore.exceptions import ClientError

        s3 = get_s3_client()
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
            filepath = DATA_DIR / csv_file
            if not filepath.is_file():
                print(f"  Skipped {csv_file} (not found in data/)")
                continue
            df = load_csv_local(str(filepath))
            load_csv_to_raw(engine, df, table_name)

    print("Done!")


if __name__ == "__main__":
    main()
