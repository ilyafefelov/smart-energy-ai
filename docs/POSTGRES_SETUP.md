# PostgreSQL Configuration & Database Setup

## Local Development Setup

### Installation

```bash
# macOS (Homebrew)
brew install postgresql

# Windows (Download from postgresql.org)
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Start service
brew services start postgresql  # macOS
# or: systemctl start postgresql  # Linux
```

### Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE smart_energy_ai;

# Create user (optional)
CREATE USER energy_user WITH PASSWORD 'dev_password';
ALTER ROLE energy_user SET client_encoding TO 'utf8';
ALTER ROLE energy_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE energy_user SET default_transaction_deferrable TO off;
ALTER ROLE energy_user SET default_transaction_read_only TO off;
ALTER ROLE energy_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE smart_energy_ai TO energy_user;

\q
```

### Connection String
```
postgresql://energy_user:dev_password@localhost:5432/smart_energy_ai
```

### Create Schema

```sql
-- Weather forecasts from Open-Meteo API
CREATE TABLE weather_forecasts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    temperature FLOAT,
    solar_radiation FLOAT,
    cloudcover FLOAT,
    wind_speed FLOAT,
    humidity FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timestamp)
);

-- Market prices from OREE Ukraine API
CREATE TABLE market_prices (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    price_eur_mwh FLOAT,
    price_uah_mwh FLOAT,
    min_price FLOAT,
    max_price FLOAT,
    source VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timestamp)
);

-- Optimization results & feedback loop
CREATE TABLE optimization_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    predicted_action INT,
    actual_action INT,
    cost_baseline FLOAT,
    cost_rl FLOAT,
    battery_soc_start FLOAT,
    battery_soc_end FLOAT,
    solar_actual FLOAT,
    load_actual FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RL training logs
CREATE TABLE rl_training_logs (
    id SERIAL PRIMARY KEY,
    training_date DATE,
    episode_count INT,
    avg_reward FLOAT,
    total_cost_savings FLOAT,
    model_version VARCHAR,
    validation_loss FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Site configuration
CREATE TABLE config (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR,
    location_lat FLOAT,
    location_lon FLOAT,
    solar_capacity_kw FLOAT,
    wind_capacity_kw FLOAT,
    battery_capacity_kwh FLOAT,
    battery_max_charge_rate_kw FLOAT,
    diesel_gen_capacity_kw FLOAT,
    diesel_fuel_cost_per_liter FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indices for performance
CREATE INDEX idx_weather_timestamp ON weather_forecasts(timestamp);
CREATE INDEX idx_prices_timestamp ON market_prices(timestamp);
CREATE INDEX idx_history_timestamp ON optimization_history(timestamp);
CREATE INDEX idx_training_date ON rl_training_logs(training_date);
```

## AWS RDS Setup (Later, Free Tier)

```bash
# Create RDS PostgreSQL instance
# Engine: PostgreSQL 14+
# Instance class: db.t3.micro (free tier)
# Storage: 20 GB (free tier)
# DB subnet group: Create new
# Public accessibility: Yes (for testing)

# Security group: Allow inbound on port 5432 from your IP

# Connection string:
postgresql://energy_user:password@smart-energy-rds.xxxxx.us-east-1.rds.amazonaws.com:5432/smart_energy_ai
```

## Environment Variables

Create `.env` file in project root:

```
DATABASE_URL=postgresql://energy_user:dev_password@localhost:5432/smart_energy_ai
OPEN_METEO_API_URL=https://api.open-meteo.com/v1/forecast
OREE_API_URL=https://www.oree.com.ua/  # May need scraping
LOG_LEVEL=INFO
```
