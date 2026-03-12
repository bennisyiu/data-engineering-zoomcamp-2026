# Version: v2.0 - Custom PySpark Dockerfile (updated for homework)
FROM apache/spark:3.5.1-python3

USER root

# Install wget for downloading datasets
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /opt/spark/requirements.txt
RUN pip install --no-cache-dir -r /opt/spark/requirements.txt

# Set working directory
WORKDIR /opt/spark/work-dir

USER spark