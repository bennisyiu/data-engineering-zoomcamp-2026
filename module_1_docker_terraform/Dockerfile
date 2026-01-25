FROM python:3.13-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ingestion script
COPY ingest_data.py .

# Set entrypoint
ENTRYPOINT ["python", "ingest_data.py"]