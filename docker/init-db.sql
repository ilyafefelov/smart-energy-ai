-- Bootstrap auxiliary local PostgreSQL databases on first container init.
\set ON_ERROR_STOP on

SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (
	SELECT 1 FROM pg_database WHERE datname = 'mlflow'
)\gexec

SELECT 'CREATE DATABASE smart_energy_ai'
WHERE NOT EXISTS (
	SELECT 1 FROM pg_database WHERE datname = 'smart_energy_ai'
)\gexec

GRANT ALL PRIVILEGES ON DATABASE mlflow TO dagster;
GRANT ALL PRIVILEGES ON DATABASE smart_energy_ai TO dagster;

\c mlflow;
GRANT ALL ON SCHEMA public TO dagster;

\c smart_energy_ai;
GRANT ALL ON SCHEMA public TO dagster;
