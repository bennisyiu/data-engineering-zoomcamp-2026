from pyspark.sql import SparkSession
from pyspark.sql.functions import col, unix_timestamp, round as spark_round
import os

spark = SparkSession.builder \
    .master("local[*]") \
    .appName("Module 6 Homework") \
    .config("spark.ui.showConsoleProgress", "false") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ============================================================
# Q1: Spark Version
# ============================================================
print("\n" + "=" * 60)
print("Q1: Spark Version")
print("=" * 60)
print(f"spark.version = {spark.version}")

# ============================================================
# Q2: Read Yellow Nov 2025, repartition to 4, save as parquet
# ============================================================
print("\n" + "=" * 60)
print("Q2: Repartitioned Parquet Average File Size")
print("=" * 60)

df = spark.read.parquet("/opt/spark/data/yellow_tripdata_2025-11.parquet")

output_path = "/opt/spark/data/output/yellow_nov_2025"
df.repartition(4).write.mode("overwrite").parquet(output_path)

parquet_files = [
    f for f in os.listdir(output_path) if f.endswith(".parquet")
]
sizes_mb = [os.path.getsize(os.path.join(output_path, f)) / (1024 * 1024) for f in parquet_files]

print(f"Number of parquet files: {len(parquet_files)}")
for name, size in zip(parquet_files, sizes_mb):
    print(f"  {name}: {size:.1f} MB")
print(f"Average size: {sum(sizes_mb) / len(sizes_mb):.1f} MB")

# ============================================================
# Q3: Count trips that started on November 15
# ============================================================
print("\n" + "=" * 60)
print("Q3: Trips starting on November 15")
print("=" * 60)

count_nov15 = df.filter(
    col("tpep_pickup_datetime").cast("date") == "2025-11-15"
).count()
print(f"Trips on Nov 15: {count_nov15:,}")

# ============================================================
# Q4: Longest trip duration in hours
# ============================================================
print("\n" + "=" * 60)
print("Q4: Longest trip duration (hours)")
print("=" * 60)

df_with_duration = df.withColumn(
    "duration_hours",
    (unix_timestamp("tpep_dropoff_datetime") - unix_timestamp("tpep_pickup_datetime")) / 3600
)
longest = df_with_duration.agg({"duration_hours": "max"}).collect()[0][0]
print(f"Longest trip: {longest:.1f} hours")

# ============================================================
# Q5: Spark UI Port (no code needed — it's 4040)
# ============================================================
print("\n" + "=" * 60)
print("Q5: Spark UI Port")
print("=" * 60)
print("Spark UI runs on port 4040")

# ============================================================
# Q6: Least frequent pickup location zone
# ============================================================
print("\n" + "=" * 60)
print("Q6: Least frequent pickup location zone")
print("=" * 60)

zones = spark.read.option("header", "true").csv("/opt/spark/data/taxi_zone_lookup.csv")
zones.createOrReplaceTempView("zones")
df.createOrReplaceTempView("trips")

least_frequent = spark.sql("""
    SELECT z.Zone, COUNT(*) as trip_count
    FROM trips t
    JOIN zones z ON t.PULocationID = z.LocationID
    GROUP BY z.Zone
    ORDER BY trip_count ASC
    LIMIT 5
""")
least_frequent.show(truncate=False)

spark.stop()
