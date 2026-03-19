"""
Upload data/*.csv to S3 under a prefix (default raw/).
Reads S3_BUCKET_NAME and S3_RAW_PREFIX from repo root .env; CLI flags override.
Run from repo root with AWS credentials (env or ~/.aws/credentials).
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

    bucket = args.bucket or os.getenv("S3_BUCKET_NAME")
    if not bucket:
        parser.error("Set S3_BUCKET_NAME in .env or pass --bucket BUCKET")

    prefix = (args.prefix or os.getenv("S3_RAW_PREFIX") or "raw").rstrip("/") + "/"

    data_dir = os.path.join(REPO_ROOT, "data")
    csv_files = ["policy.csv", "invoice.csv", "claim.csv"]

    import boto3
    s3 = boto3.client("s3")
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
