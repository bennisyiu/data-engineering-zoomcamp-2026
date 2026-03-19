# S3 Setup for Pipeline

The pipeline reads the three CSVs from S3 when `S3_BUCKET_NAME` is set in the root `.env`. Use this guide to create the bucket and upload files.

---

## 1. Create an S3 bucket (AWS Console or CLI)

- **Console:** S3 → Create bucket → choose a globally unique name (e.g. `bennis-insurance-dwh-raw`) and region (e.g. `ap-southeast-1`). Block public access is fine; the pipeline uses IAM.
- **CLI:**
  ```bash
  aws s3 mb s3://YOUR-BUCKET-NAME --region ap-southeast-1
  ```

---

## 2. Upload the CSVs

The pipeline expects these object keys (prefix = `S3_RAW_PREFIX`, default `raw`):

| Key in bucket |
|---------------|
| `raw/policy.csv` |
| `raw/invoice.csv` |
| `raw/claim.csv` |

### Option A: Upload script (from your laptop, with AWS credentials)

Set `S3_BUCKET_NAME` (and optionally `S3_RAW_PREFIX`) in the repo root `.env`, then from the **repo root**:

```bash
python scripts/upload_to_s3.py
```

The script reads bucket and prefix from `.env`. You can override with flags:

```bash
python scripts/upload_to_s3.py --bucket OTHER-BUCKET --prefix raw
```

### Option B: AWS Console

1. Open your bucket → Create folder → name it `raw`.
2. Open `raw` → Upload → add `policy.csv`, `invoice.csv`, `claim.csv` from your local `data/` folder.

### Option C: AWS CLI

From repo root:

```bash
aws s3 cp data/policy.csv s3://YOUR-BUCKET-NAME/raw/
aws s3 cp data/invoice.csv s3://YOUR-BUCKET-NAME/raw/
aws s3 cp data/claim.csv s3://YOUR-BUCKET-NAME/raw/
```

---

## 3. IAM / credentials

- **EC2:** Attach an IAM role to the instance with S3 read (e.g. `AmazonS3ReadOnlyAccess` or a policy that allows `s3:GetObject` on this bucket). No keys in `.env` on EC2.
- **Local / upload script:** Use an IAM user with S3 read+write, and set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` in `.env` or in `~/.aws/credentials`.

---

## 4. Configure the project

In the **repo root** `.env` (on EC2 and/or local if you run the pipeline against S3):

```env
S3_BUCKET_NAME=YOUR-BUCKET-NAME
S3_RAW_PREFIX=raw
```

Leave `S3_BUCKET_NAME` empty to use local `data/` instead of S3.

---

## 5. Verify

After the next DAG run (or manual `python scripts/extract_load.py`), check that the `raw` schema in the warehouse has `raw_policy`, `raw_invoice`, `raw_claim` with row counts matching your CSVs.
