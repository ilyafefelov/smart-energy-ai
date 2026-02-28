FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install MLflow
RUN pip install --no-cache-dir mlflow boto3

# Install PostgreSQL client for MLflow
RUN pip install --no-cache-dir psycopg2-binary

# Set Dagster home
ENV DAGSTER_HOME=/app/.dagster

# Expose ports
EXPOSE 3000 5000

# Default command runs Dagster
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000"]
