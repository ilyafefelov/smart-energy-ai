# Smart Energy AI - Production Container
#
# Multi-stage Dockerfile:
#   - Stage 1: Builder (installs dependencies)
#   - Stage 2: Runtime (minimal production image)
#
# Usage:
#   docker build -t smart-energy-ai .
#   docker run -p 3000:3000 smart-energy-ai

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim

# Labels
LABEL org.opencontainers.image.title="Smart Energy AI"
LABEL org.opencontainers.image.description="Energy optimization with battery scheduling and ML"
LABEL org.opencontainers.image.source="https://github.com/ilyafefelov/smart-energy-ai"

# Security: Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup energy_ml/ ./energy_ml/
COPY --chown=appuser:appgroup data/ ./data/
COPY --chown=appuser:appgroup models/ ./models/
COPY --chown=appuser:appgroup tests/ ./tests/
COPY --chown=appuser:appgroup *.py ./
COPY --chown=appuser:appgroup *.txt ./
COPY --chown=appuser:appgroup *.md ./
COPY --chown=appuser:appgroup .env.example .env

# Create directories for runtime data
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app

# Environment defaults (can be overridden at runtime)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DAGSTER_HOME=/app/data/dagster_home \
    LOG_LEVEL=INFO \
    PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 3000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:3000/health', timeout=5)" || exit 1

# Default: Run Dagster
# Override with: docker run smart-energy-ai python -m src.cli optimize
CMD ["python", "-m", "dagster", "dev", "-h", "0.0.0.0", "-p", "3000"]
