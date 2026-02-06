-- Question 1. What is count of records for the 2024 Yellow Taxi Data?

SELECT COUNT(*) AS record_count
FROM `zoomcamp.yellow_taxi_trips_2024`;


-- Question 2. What is the estimated amount of data that will be read when this query is executed on the External Table and the Table?
-- Answer: 0 MB for the External Table and 155.12 MB for the Materialized Table
-- Reasoning: BigQuery cannot estimate bytes for external tables (data lives outside BQ storage),
-- so it shows 0 MB. For native/materialized tables, BQ knows the stored size from internal metadata.

-- Question 3. Why are the estimated number of Bytes different?
-- Answer: BigQuery is a columnar database, and it only scans the specific columns requested.
-- Querying two columns (PULocationID, DOLocationID) reads more data than querying one column (PULocationID).

-- Question 4. How many records have a fare_amount of 0? 
SELECT count(*) FROM `inlaid-rig-385510.zoomcamp.yellow_taxi_trips_2024` 
where fare_amount = 0
-- Answer: 80333


-- Question 5. What is the best strategy to make an optimized table in Big Query if your query will always filter
-- based on tpep_dropoff_datetime and order the results by VendorID (Create a new table with this strategy)
-- Answer: Partition by tpep_dropoff_datetime and Cluster on VendorID

-- Create the optimized table:
CREATE OR REPLACE TABLE `zoomcamp.yellow_taxi_trips_2024_partitioned_clustered`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID
AS
SELECT * FROM `zoomcamp.yellow_taxi_trips_2024`;


-- Question 6. Write a query to retrieve the distinct VendorIDs between tpep_dropoff_datetime 2024-03-01 and 2024-03-15 (inclusive).
-- Use the materialized table you created earlier in your from clause and note the estimated bytes.
-- Now change the table in the from clause to the partitioned table you created for question 5 and note the estimated bytes processed.
-- What are these values?

-- Query on the non-partitioned (materialized) table:
SELECT DISTINCT VendorID
FROM `zoomcamp.yellow_taxi_trips_2024`
WHERE tpep_dropoff_datetime BETWEEN '2024-03-01' AND '2024-03-15';
-- Answer: 310.24MB

-- Query on the partitioned + clustered table:
SELECT DISTINCT VendorID
FROM `zoomcamp.yellow_taxi_trips_2024_partitioned_clustered`
WHERE tpep_dropoff_datetime BETWEEN '2024-03-01' AND '2024-03-15';
-- Answer: 26.84MB


-- Question 7. Where is the data stored in the External Table you created?
-- Answer: GCP Bucket (Google Cloud Storage)
-- External tables don't store data in BigQuery — they reference files in GCS.

-- Question 8. It is best practice in Big Query to always cluster your data:
-- Answer: No (False)
-- Clustering is not always beneficial. For small tables (<1GB), the overhead isn't worth it.
-- If queries don't filter/order by the clustered columns, there's no performance gain.

-- Question 9. Write a `SELECT count(*)` query FROM the materialized table you created.
-- How many bytes does it estimate will be read? Why? (not graded)

SELECT COUNT(*) FROM `zoomcamp.yellow_taxi_trips_2024_partitioned_clustered`;

-- Answer: 0 bytes estimated.
-- BigQuery stores row count in internal metadata. For a simple COUNT(*) with no WHERE clause,
-- it returns the count directly from metadata without scanning any table data.