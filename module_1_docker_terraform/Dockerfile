FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest_data.py ingest_green_taxi.py ingest_zones.py ./

# Set entrypoint to python, default to ingest_data.py
ENTRYPOINT ["python"]
CMD ["ingest_data.py"]