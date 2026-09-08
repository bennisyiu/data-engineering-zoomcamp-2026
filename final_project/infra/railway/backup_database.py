"""Create a compressed logical PostgreSQL backup in Railway object storage."""

from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or os.getenv("ENDPOINT"),
        region_name=os.getenv("AWS_REGION") or os.getenv("REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        or os.getenv("SECRET_ACCESS_KEY"),
    )


def main() -> None:
    database_url = os.getenv("BACKUP_DATABASE_URL") or os.getenv("DATABASE_URL")
    bucket = os.getenv("S3_BUCKET_NAME") or os.getenv("BUCKET")
    if not database_url or not bucket:
        raise RuntimeError("Set BACKUP_DATABASE_URL/DATABASE_URL and S3_BUCKET_NAME/BUCKET")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"backups/insurance_dwh-{stamp}.dump"
    with tempfile.TemporaryDirectory() as directory:
        dump_path = Path(directory) / "insurance_dwh.dump"
        subprocess.run(
            [
                "pg_dump",
                "--dbname",
                database_url,
                "--format=custom",
                "--compress=9",
                "--no-owner",
                "--no-acl",
                "--file",
                str(dump_path),
            ],
            check=True,
        )
        subprocess.run(
            ["pg_restore", "--list", str(dump_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print("Validated logical backup with pg_restore --list")
        s3 = get_s3_client()
        s3.upload_file(str(dump_path), bucket, key)
        print(f"Uploaded logical backup to s3://{bucket}/{key}")

    keep = int(os.getenv("BACKUP_RETENTION_COUNT", "6"))
    response = s3.list_objects_v2(Bucket=bucket, Prefix="backups/")
    objects = sorted(response.get("Contents", []), key=lambda item: item["LastModified"])
    for item in objects[:-keep]:
        s3.delete_object(Bucket=bucket, Key=item["Key"])
        print(f"Removed expired backup {item['Key']}")


if __name__ == "__main__":
    main()
