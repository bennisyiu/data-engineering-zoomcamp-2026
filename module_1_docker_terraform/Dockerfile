# Base image
FROM python:3.11.9-slim

# Set working directory
WORKDIR /app

# Copy dependencies file and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY pipeline.py pipeline.py

# Set entry point
ENTRYPOINT ["python", "pipeline.py"]