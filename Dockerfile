FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r energy_ml/requirements.txt

# Set Dagster home
ENV DAGSTER_HOME=/app/.dagster

# Expose Dagster UI port
EXPOSE 3000

# Run Dagster
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000"]
