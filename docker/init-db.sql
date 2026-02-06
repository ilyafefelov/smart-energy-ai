-- Initialize databases for Dagster and MLflow
CREATE DATABASE IF NOT EXISTS mlflow;
CREATE USER IF NOT EXISTS mlflow WITH PASSWORD 'mlflow123';
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;