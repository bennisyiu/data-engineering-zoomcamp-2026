import io
import json
import urllib.request
import pyarrow.parquet as pq  # used for reading parquet metadata
from google.cloud import bigquery
from google.oauth2 import service_account

# Load BigQuery service account key from local credentials file
with open("credentials.json") as f:
    creds= json.load(f)
    
bq_credentials_dict = creds['bigquery']

# Create credentials object from service account dict
credentials = service_account.Credentials.from_service_account_info(bq_credentials_dict)

# Initialize BigQuery client
client_bq = bigquery.Client(credentials=credentials, project=bq_credentials_dict['project_id'])

# Define parameters
project_id = bq_credentials_dict['project_id']
dataset_id = 'zoomcamp'
table_name = 'yellow_taxi_trips_2024'
table_id = f"{project_id}.{dataset_id}.{table_name}"

base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-{}.parquet"
required_months = ['01', '02', '03', '04', '05', '06']

# Define schema matching your table structure
schema = [
    bigquery.SchemaField("VendorID", "INTEGER"),
    bigquery.SchemaField("tpep_pickup_datetime", "TIMESTAMP"),
    bigquery.SchemaField("tpep_dropoff_datetime", "TIMESTAMP"),
    bigquery.SchemaField("passenger_count", "INTEGER"),
    bigquery.SchemaField("trip_distance", "FLOAT"),
    bigquery.SchemaField("RatecodeID", "INTEGER"),
    bigquery.SchemaField("store_and_fwd_flag", "STRING"),
    bigquery.SchemaField("PULocationID", "INTEGER"),
    bigquery.SchemaField("DOLocationID", "INTEGER"),
    bigquery.SchemaField("payment_type", "INTEGER"),
    bigquery.SchemaField("fare_amount", "FLOAT"),
    bigquery.SchemaField("extra", "FLOAT"),
    bigquery.SchemaField("mta_tax", "FLOAT"),
    bigquery.SchemaField("tip_amount", "FLOAT"),
    bigquery.SchemaField("tolls_amount", "FLOAT"),
    bigquery.SchemaField("improvement_surcharge", "FLOAT"),
    bigquery.SchemaField("total_amount", "FLOAT"),
    bigquery.SchemaField("congestion_surcharge", "FLOAT"),
]

# Create table with partitioning on pickup datetime
table = bigquery.Table(table_id, schema=schema)
table.time_partitioning = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.DAY,
    field="tpep_pickup_datetime"
)

# Create table if not exists
table = client_bq.create_table(table, exists_ok=True)
print(f"Table {table_id} is ready (partitioned by tpep_pickup_datetime)")

# Load data for each month
for month in required_months:
    url = base_url.format(month)
    
    print(f"Loading data for 2024-{month}...")
    
    # Download parquet file
    response = urllib.request.urlopen(url)
    parquet_data = io.BytesIO(response.read())
    row_count = pq.read_metadata(parquet_data).num_rows
    parquet_data.seek(0)

    # Load to BigQuery
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition="WRITE_APPEND"
    )

    job = client_bq.load_table_from_file(parquet_data, table_id, job_config=job_config)
    job.result()  # Wait for completion

    print(f"Successfully loaded {row_count} rows for 2024-{month}")

print("All months loaded successfully")