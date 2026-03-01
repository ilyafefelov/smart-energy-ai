-- Initialize databases for Dagster and MLflow

-- Create Dagster database and user
CREATE DATABASE dagster;
CREATE USER dagster WITH PASSWORD 'dagster';
GRANT ALL PRIVILEGES ON DATABASE dagster TO dagster;

-- Create MLflow database and user  
CREATE DATABASE mlflow;
CREATE USER mlflow WITH PASSWORD 'mlflow123';
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow;

-- Grant schema permissions
\c dagster;
GRANT ALL ON SCHEMA public TO dagster;

\c mlflow;
GRANT ALL ON SCHEMA public TO mlflow;
