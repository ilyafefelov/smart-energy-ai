# Smart Energy AI V2 - Docker Configuration
# Multi-stage build for production deployment

# Stage 1: Base Python environment
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DAGSTER_HOME=/opt/dagster/dagster_home

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Stage 2: Dependencies installation
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .
COPY docker/requirements-prod.txt ./docker/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r docker/requirements-prod.txt

# Stage 3: Application code
FROM dependencies as application

# Copy application code
COPY src/ ./src/
COPY customers.yaml .
COPY dagster.yaml .
COPY workspace.yaml .

# Create Dagster directories
RUN mkdir -p $DAGSTER_HOME/storage
RUN mkdir -p $DAGSTER_HOME/logs

# Copy Dagster configuration
COPY docker/dagster.yaml $DAGSTER_HOME/
COPY docker/workspace.yaml $DAGSTER_HOME/

# Stage 4: Production image
FROM application as production

# Create non-root user for security
RUN groupadd -r dagster && useradd -r -g dagster dagster
RUN chown -R dagster:dagster /app
RUN chown -R dagster:dagster $DAGSTER_HOME

USER dagster

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Expose Dagster webserver port
EXPOSE 3000

# Default command (can be overridden)
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]

# Stage 5: Development image
FROM application as development

# Install development dependencies
COPY docker/requirements-dev.txt ./docker/
RUN pip install --no-cache-dir -r docker/requirements-dev.txt

# Install Jupyter and development tools
RUN pip install jupyter jupyterlab

# Expose additional ports for development
EXPOSE 3000 8888 5000

# Development command
CMD ["bash"]