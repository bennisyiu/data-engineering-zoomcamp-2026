"""
PyFlink streaming job: Kafka topic -> JDBC sink into raw_streaming.stream_policy_events.

Uses the DataStream API + FlinkKafkaConsumer + JdbcSink (Table API JDBC fat jar is not
published for 1.18 on Maven Central; flink-connector-jdbc works with PyFlink JdbcSink).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from pyflink.common import Row
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import RowTypeInfo, Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.jdbc import (
    JdbcConnectionOptions,
    JdbcExecutionOptions,
    JdbcSink,
)
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
from pyflink.datastream.functions import MapFunction


class ParseEvent(MapFunction):
    def map(self, value: str) -> Row:
        o = json.loads(value)
        ms = int(o["event_time_ms"])
        # Naive UTC for java.sql.Timestamp / JDBC
        dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
        payload = o.get("payload", "{}")
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        return Row(o["policy_number"], o["event_type"], payload[:8000], dt)


def main() -> None:
    kafka_bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    kafka_topic = os.environ.get("KAFKA_TOPIC", "policy_events")
    pg_host = os.environ.get("POSTGRES_HOST", "warehouse")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_db = os.environ.get("POSTGRES_DB", "insurance_dwh")
    pg_user = os.environ["POSTGRES_USER"]
    pg_password = os.environ["POSTGRES_PASSWORD"]

    jdbc_url = f"jdbc:postgresql://{pg_host}:{pg_port}/{pg_db}"

    row_type = RowTypeInfo(
        [Types.STRING(), Types.STRING(), Types.STRING(), Types.SQL_TIMESTAMP()],
        ["policy_number", "event_type", "payload", "event_time"],
    )

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    jar_dir = "/opt/flink/lib"
    # kafka-clients lives in /opt/flink/lib only; do not add_jars it — duplicate loading
    # causes ByteArrayDeserializer "not an instance of Deserializer" (split classloaders).
    env.add_jars(
        f"file://{jar_dir}/flink-connector-kafka-3.0.2-1.18.jar",
        f"file://{jar_dir}/flink-connector-jdbc-3.1.2-1.18.jar",
        f"file://{jar_dir}/postgresql-42.7.2.jar",
    )

    print("Waiting for Kafka to be ready...", flush=True)
    time.sleep(5)

    props = {
        "bootstrap.servers": kafka_bootstrap,
        "group.id": "flink-insurance-stream",
    }
    consumer = FlinkKafkaConsumer(kafka_topic, SimpleStringSchema(), props)
    consumer.set_start_from_earliest()

    stream = env.add_source(consumer).map(ParseEvent(), output_type=row_type)

    insert_sql = (
        "INSERT INTO raw_streaming.stream_policy_events "
        "(policy_number, event_type, payload, event_time) VALUES (?, ?, ?, ?)"
    )

    exec_opts = (
        JdbcExecutionOptions.builder()
        .with_batch_interval_ms(5000)
        .with_batch_size(10)
        .with_max_retries(3)
        .build()
    )

    conn_opts = (
        JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
        .with_url(jdbc_url)
        .with_driver_name("org.postgresql.Driver")
        .with_user_name(pg_user)
        .with_password(pg_password)
        .build()
    )

    stream.add_sink(JdbcSink.sink(insert_sql, row_type, conn_opts, exec_opts))

    print(
        f"Executing Flink job: kafka={kafka_bootstrap!r} topic={kafka_topic!r} "
        f"jdbc={jdbc_url!r}",
        flush=True,
    )
    env.execute("insurance-kafka-to-postgres-stream")


if __name__ == "__main__":
    main()
