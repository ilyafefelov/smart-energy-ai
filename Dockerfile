# Smart Energy AI - Development Container
#
# This Dockerfile sets up a development environment with:
# - Python 3.11
# - PostgreSQL client
# - MLflow and dependencies
#
# Usage:
#   docker build -t smart-energy-ai .
#   docker run -it -p 3000:3000 -p 5000:5000 smart-energy-ai
#
# Note: Run Dagster locally with: python -m dagster dev -h 0.0.0.0 -p 3000

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install MLflow and boto3 for S3-compatible storage
RUN pip install --no-cache-dir mlflow boto3

# Copy project files
COPY . /app/

# Set environment
ENV DAGSTER_HOME=/app/.dagster
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 3000 5000

# Default: stay running (use docker exec to run commands)
CMD ["tail", "-f", "/dev/null"]
