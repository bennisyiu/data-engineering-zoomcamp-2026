"""
Upload data/*.csv to AWS S3 or S3-compatible storage under raw/ by default.
Supports Railway Storage Bucket variables as well as standard AWS variables.
Usage: python scripts/upload_to_s3.py   [uses .env]
       python scripts/upload_to_s3.py --bucket OTHER_BUCKET
"""
import argparse
import os

# Load .env from repo root (parent of scripts/)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_env_path = os.path.join(REPO_ROOT, ".env")


def main():
    parser = argparse.ArgumentParser(description="Upload CSVs from data/ to S3")
    parser.add_argument("--bucket", help="S3 bucket (overrides S3_BUCKET_NAME in .env)")
    parser.add_argument("--prefix", help="S3 key prefix (overrides S3_RAW_PREFIX in .env)")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(_env_path)

    bucket = args.bucket or os.getenv("S3_BUCKET_NAME") or os.getenv("BUCKET")
    if not bucket:
        parser.error("Set S3_BUCKET_NAME/BUCKET or pass --bucket BUCKET")

    prefix = (args.prefix or os.getenv("S3_RAW_PREFIX") or "raw").rstrip("/") + "/"

    data_dir = os.path.join(REPO_ROOT, "data")
    csv_files = ["policy.csv", "invoice.csv", "claim.csv"]

    import boto3
    endpoint = os.getenv("S3_ENDPOINT_URL") or os.getenv("ENDPOINT")
    region = os.getenv("AWS_REGION") or os.getenv("REGION")
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("SECRET_ACCESS_KEY")
    kwargs = {}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    if region:
        kwargs["region_name"] = region
    if access_key:
        kwargs["aws_access_key_id"] = access_key
    if secret_key:
        kwargs["aws_secret_access_key"] = secret_key
    s3 = boto3.client("s3", **kwargs)

    for name in csv_files:
        path = os.path.join(data_dir, name)
        if not os.path.isfile(path):
            print(f"Skipped {name} (not found)")
            continue
        key = prefix + name
        s3.upload_file(path, bucket, key)
        print(f"Uploaded {path} -> s3://{bucket}/{key}")

    print("Done.")


if __name__ == "__main__":
    main()
