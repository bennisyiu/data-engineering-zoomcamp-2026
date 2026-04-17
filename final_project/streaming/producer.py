"""
Publish synthetic policy-style events to Kafka for the PyFlink stream path.

Run inside Docker (see infra/docker-compose.yml) or locally with:
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python producer.py
"""

from __future__ import annotations

import json
import os
import random
import time

from kafka import KafkaProducer

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "policy_events")
INTERVAL_SEC = float(os.environ.get("PRODUCER_INTERVAL_SEC", "5"))


def main() -> None:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=100,
    )
    policies = [f"P-DEMO-{i:04d}" for i in range(1, 51)]
    types = ("stream_heartbeat", "policy_viewed", "quote_requested", "premium_reminder")

    print(f"Producer: bootstrap={BOOTSTRAP!r} topic={TOPIC!r}", flush=True)
    n = 0
    while True:
        n += 1
        event = {
            "policy_number": random.choice(policies),
            "event_type": random.choice(types),
            "payload": json.dumps({"seq": n, "source": "demo_producer"}),
            "event_time_ms": int(time.time() * 1000),
        }
        producer.send(TOPIC, value=event)
        producer.flush()
        print(f"Sent {n}: {event['policy_number']} {event['event_type']}", flush=True)
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
