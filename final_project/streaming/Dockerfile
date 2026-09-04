# PyFlink + Kafka + JDBC connectors (Kafka → Postgres stream landing zone).
FROM flink:1.18.1-scala_2.12-java11

USER root
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3 python3-pip python3-dev wget; \
    rm -rf /var/lib/apt/lists/*; \
    ln -sf /usr/bin/python3 /usr/bin/python; \
    pip3 install --no-cache-dir apache-flink==1.18.1; \
    wget -q -O /opt/flink/lib/flink-connector-kafka-3.0.2-1.18.jar \
      https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.0.2-1.18/flink-connector-kafka-3.0.2-1.18.jar; \
    wget -q -O /opt/flink/lib/kafka-clients-3.2.3.jar \
      https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.2.3/kafka-clients-3.2.3.jar; \
    wget -q -O /opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar \
      https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar; \
    wget -q -O /opt/flink/lib/postgresql-42.7.2.jar \
      https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.2/postgresql-42.7.2.jar

WORKDIR /opt/flink/usrlib
COPY job.py .

RUN chown flink:flink /opt/flink/usrlib/job.py
USER flink

CMD ["python", "job.py"]
