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

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

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
    user = quote_plus(DB_USER or "")
    password = quote_plus(DB_PASSWORD or "")
    url = f"postgresql://{user}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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
    print(f"Connected to {DB_NAME} at {DB_HOST}:{DB_PORT}")
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
