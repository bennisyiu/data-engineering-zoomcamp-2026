import argparse
import re
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud import bigquery

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
PICKUP_COLUMNS = {
    "yellow": "tpep_pickup_datetime",
    "green": "lpep_pickup_datetime",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download NYC taxi parquet files and load them into BigQuery."
    )
    parser.add_argument("--project-id", required=True, help="GCP project id")
    parser.add_argument("--dataset", default="raw_ny_taxi", help="BigQuery dataset name")
    parser.add_argument(
        "--taxi-types",
        nargs="+",
        default=["yellow", "green"],
        choices=["yellow", "green"],
        help="Taxi types to ingest",
    )
    parser.add_argument("--start-year", type=int, default=2019, help="Start year (inclusive)")
    parser.add_argument("--end-year", type=int, default=2020, help="End year (inclusive)")
    parser.add_argument("--location", default="US", help="BigQuery dataset location")
    parser.add_argument(
        "--replace-tables",
        action="store_true",
        help="Drop destination tables before loading data",
    )
    return parser.parse_args()


def ensure_dataset(client, dataset_id, location):
    dataset_ref = bigquery.Dataset(f"{client.project}.{dataset_id}")
    dataset_ref.location = location
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset ready: {client.project}.{dataset_id}")


def maybe_drop_table(client, table_id):
    client.delete_table(table_id, not_found_ok=True)
    print(f"Dropped table (if it existed): {table_id}")


def table_exists(client, table_id):
    try:
        client.get_table(table_id)
        return True
    except NotFound:
        return False


def download_file(url, target_path):
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(target_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_handle.write(chunk)


def extract_integer_to_float_field(error_message):
    pattern = r"Field\s+([A-Za-z_][A-Za-z0-9_]*)\s+has changed type from (?:INTEGER|INT64) to (?:FLOAT|FLOAT64)"
    match = re.search(pattern, error_message, flags=re.IGNORECASE)
    return match.group(1) if match else None


def extract_type_change(error_message):
    pattern = (
        r"Field\s+([A-Za-z_][A-Za-z0-9_]*)\s+has changed type from "
        r"([A-Za-z0-9_]+)\s+to\s+([A-Za-z0-9_]+)"
    )
    match = re.search(pattern, error_message, flags=re.IGNORECASE)
    if not match:
        return None, None, None
    return match.group(1), match.group(2).upper(), match.group(3).upper()


def is_int_float_mismatch(from_type, to_type):
    int_types = {"INTEGER", "INT64"}
    float_types = {"FLOAT", "FLOAT64"}
    return (from_type in int_types and to_type in float_types) or (
        from_type in float_types and to_type in int_types
    )


def extract_parquet_type_mismatch(error_message):
    pattern = (
        r"Parquet column '([A-Za-z_][A-Za-z0-9_]*)' has type [A-Za-z0-9_]+ "
        r"which does not match the target cpp_type DOUBLE"
    )
    match = re.search(pattern, error_message, flags=re.IGNORECASE)
    return match.group(1) if match else None


def normalize_parquet_column_to_float(local_path, column_name):
    table = pq.read_table(local_path)
    if column_name not in table.schema.names:
        return False
    field_index = table.schema.get_field_index(column_name)
    casted_column = table[column_name].cast(pa.float64())
    normalized_table = table.set_column(field_index, column_name, casted_column)
    pq.write_table(normalized_table, local_path, compression="snappy")
    print(f"Normalized parquet column to FLOAT64: {local_path.name}.{column_name}")
    return True


def promote_column_to_float(client, table_id, column_name):
    query = (
        f"ALTER TABLE `{table_id}` "
        f"ALTER COLUMN `{column_name}` "
        "SET DATA TYPE FLOAT64"
    )
    client.query(query).result()
    print(f"Promoted column type to FLOAT64: {table_id}.{column_name}")


def load_single_file(client, local_path, table_id, pickup_column):
    def make_job_config(use_existing_schema):
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            autodetect=not use_existing_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            time_partitioning=bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field=pickup_column,
            ),
            schema_update_options=[
                bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
                bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
            ],
        )
        if use_existing_schema:
            job_config.schema = client.get_table(table_id).schema
        return job_config

    # Some months contain schema drift (example: airport_fee flips between int/float).
    # Retry with destination schema to normalize file-level type differences.
    use_existing_schema = False
    for attempt in range(3):
        try:
            job_config = make_job_config(use_existing_schema)
            with open(local_path, "rb") as parquet_file:
                load_job = client.load_table_from_file(parquet_file, table_id, job_config=job_config)
                load_job.result()
            break
        except BadRequest as error:
            error_text = str(error)
            drift_column, from_type, to_type = extract_type_change(error_text)
            if drift_column and is_int_float_mismatch(from_type, to_type) and attempt < 2:
                if to_type in {"FLOAT", "FLOAT64"}:
                    promote_column_to_float(client, table_id, drift_column)
                if from_type in {"FLOAT", "FLOAT64"} and to_type in {"INTEGER", "INT64"}:
                    # Ensure destination stays FLOAT64 to accept both integer and float months.
                    promote_column_to_float(client, table_id, drift_column)
                    normalize_parquet_column_to_float(local_path, drift_column)
                use_existing_schema = True
                print(f"Retrying load after schema promotion: {local_path.name}")
                continue
            parquet_mismatch_column = extract_parquet_type_mismatch(error_text)
            if parquet_mismatch_column and attempt < 2:
                promote_column_to_float(client, table_id, parquet_mismatch_column)
                normalized = normalize_parquet_column_to_float(local_path, parquet_mismatch_column)
                if normalized:
                    use_existing_schema = True
                    print(f"Retrying load after parquet normalization: {local_path.name}")
                    continue
            raise

    loaded_table = client.get_table(table_id)
    return loaded_table.num_rows


def ingest_taxi_type(client, dataset, taxi_type, years):
    table_id = f"{client.project}.{dataset}.{taxi_type}_tripdata"
    pickup_column = PICKUP_COLUMNS[taxi_type]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        for year in years:
            for month in range(1, 13):
                parquet_file = f"{taxi_type}_tripdata_{year}-{month:02d}.parquet"
                parquet_url = f"{BASE_URL}/{parquet_file}"
                local_path = temp_dir_path / parquet_file

                print(f"Downloading {parquet_file}...")
                download_file(parquet_url, local_path)

                print(f"Loading {parquet_file} into {table_id}...")
                total_rows = load_single_file(client, local_path, table_id, pickup_column)
                print(f"Loaded {parquet_file}. Current table rows: {total_rows}")


def main():
    args = parse_args()
    if args.end_year < args.start_year:
        raise ValueError("--end-year must be >= --start-year")

    years = range(args.start_year, args.end_year + 1)
    client = bigquery.Client(project=args.project_id)

    ensure_dataset(client, args.dataset, args.location)

    if args.replace_tables:
        for taxi_type in args.taxi_types:
            table_id = f"{args.project_id}.{args.dataset}.{taxi_type}_tripdata"
            maybe_drop_table(client, table_id)

    for taxi_type in args.taxi_types:
        table_id = f"{args.project_id}.{args.dataset}.{taxi_type}_tripdata"
        if not table_exists(client, table_id):
            print(f"Table does not exist yet and will be created: {table_id}")
        ingest_taxi_type(client, args.dataset, taxi_type, years)

    print("Ingestion complete.")


if __name__ == "__main__":
    main()