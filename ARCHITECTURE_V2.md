# Smart Energy AI - V2 Architecture: ETL/ELT + RL Pipeline

## Overview
Upgrade from static model to production-ready data pipeline with reinforcement learning for continuous optimization.

## Current vs Target

### Current (V1 - Static)
```
Fixed RF Model → Scenario Rules → Daily CSV Output
```

### Target (V2 - Dynamic)
```
ETL Pipeline → RL Agent → Real-time Optimization → Feedback Loop → Retrain
```

---

## Data Pipeline Architecture

### 1. Inbound Data Layers

#### Weather Data
- **Source:** Open-Meteo API (free, no auth needed)
- **Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Frequency:** Daily at 6:00 AM (24h ahead forecast)
- **Fields:** temperature, solar_radiation, cloudcover, wind_speed, humidity
- **Location:** Kyiv (50.45°N, 30.52°E)
- **Storage:** PostgreSQL `weather_forecasts` table + CSV cache
- **Validation:** Check for NaN, outliers (radiation > 2000 W/m²), missing hours

#### Market Price Data
- **Source:** OREE API (Ukrainian Day-Ahead Market)
- **Endpoint:** `https://www.oree.com.ua/` (may need scraping)
- **Frequency:** Daily (updated ~3 PM for next day 00:00-24:00)
- **Fields:** hour, price_uah_mwh, min_price, max_price
- **Storage:** PostgreSQL `market_prices` table
- **Validation:** Check price bounds (realistic range: 1-15 EUR/MWh), gaps

#### Plant/IoT Data (Simulated → Real)
- **Simulated:** Historical patterns + random noise
- **Target Real:** MQTT topics or REST API from SCADA system
- **Frequency:** Hourly aggregates or 15-min raw
- **Fields:** solar_gen_actual, load_actual, battery_soc, battery_temp, inverter_status
- **Storage:** InfluxDB (time-series) or PostgreSQL
- **Validation:** Sensor health checks, range validation

### 2. Processing Layers (ELT)

#### Feature Engineering
```
Raw data → Normalized features → Model inputs

Inputs for RL:
- Current hour (0-23)
- Day of week (0-6)
- Season (0-3)
- Price (EUR/MWh)
- Solar forecast (kW)
- Load forecast (kW)
- Battery SOC (%)
- Previous action taken
```

#### Historical Data Aggregation
- Merge 24h price + weather + actual results
- Calculate: Prediction errors, cost delta, efficiency metrics
- Create training dataset for RL agent

#### Feedback Loop
- Log actual executed action (what SCADA did)
- Compare to recommended action (what RL suggested)
- Calculate actual cost vs baseline
- Store in `optimization_history` table for analysis

### 3. Outbound Data Layers

#### Daily Action Plan
- **Output:** JSON + CSV
- **Fields:** hour, recommended_action, confidence, estimated_savings
- **Consumers:** SCADA system, Dashboard, Reporting
- **Format:** REST API endpoint + file export

#### Analytics & Reporting
- **RL Agent Performance:** Cumulative savings, win rate vs baseline
- **Forecast Accuracy:** MAPE (Mean Absolute Percentage Error) for prices/solar
- **System Health:** Uptime, data freshness, API latency
- **Dashboard:** Real-time + historical views

---

## Reinforcement Learning Agent

### State Space (Input to RL)
```python
state = {
    'hour': int (0-23),
    'price_current': float (EUR/MWh),
    'price_next': float (forecast),
    'solar_actual': float (kW),
    'solar_forecast': float (kW),
    'load_actual': float (kW),
    'load_forecast': float (kW),
    'battery_soc': float (0-100%),
    'battery_temp': float (°C),
    'day_of_week': int (0-6),
    'season': int (0-3),
    'prev_action': int (0-4),
}
```

### Action Space (Output of RL)
```
0: CHARGE_FROM_GRID (aggressive charging at low prices)
1: DISCHARGE_BATTERY (use stored energy at high prices)
2: STORE_SOLAR (store excess renewable)
3: SELL_TO_GRID (sell excess to network)
4: IDLE (buy minimum, no special action)
```

### Reward Function
```
Daily Reward = -(Actual Cost - Baseline Cost)

Baseline = always buy from grid at market prices

Bonus rewards:
+ Successfully avoided peak pricing (discharge at right time)
+ Captured free solar energy
+ Sold back to grid profitably
- Battery depth of discharge too high
- Forecast error penalties
```

### Training Pipeline
```
1. Collect 24h of data (prices, weather, actions, actual costs)
2. Normalize state features (min-max scaling)
3. Train RL agent on yesterday's data (offline)
4. Validate on day-before-yesterday (holdout test)
5. Deploy for today's optimization
6. Log decisions for next cycle
```

### RL Algorithm: PPO (Proximal Policy Optimization)
- **Why PPO:** Stable, sample-efficient, handles continuous + discrete actions
- **Library:** Stable-Baselines3
- **Hyperparameters:** (to be tuned)
  - Learning rate: 3e-4
  - Batch size: 32
  - Training epochs: 10
  - GAE lambda: 0.95

---

## Daily Automation Workflow

### Schedule
```
06:00 - Fetch new data (weather, prices)
06:10 - Preprocess & validate
06:15 - Train RL agent on yesterday's data
06:30 - Generate today's action plan
08:00 - Push recommendations to SCADA
08:00-30:00 - Execute actions, log results
Next 06:00 - Feedback evaluation, loop restarts
```

### Orchestration Tool Options

#### Option A: Airflow
- Pros: Powerful, industry standard, great UI
- Cons: Heavier, steeper learning curve
- Use if: You want production-grade DAG management

#### Option B: Prefect
- Pros: Modern, Pythonic, easier, better error handling
- Cons: Newer, smaller community
- Use if: You prefer simplicity + good DX

#### Option C: APScheduler + Cron
- Pros: Lightweight, no external service
- Cons: Less robust, harder to debug
- Use if: POC/capstone phase (easiest start)

**Recommendation for capstone:** APScheduler (simple) → migrate to Airflow later

---

## Database Schema

### PostgreSQL Tables

```sql
-- Weather Data
CREATE TABLE weather_forecasts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperature FLOAT,
    solar_radiation FLOAT,
    cloudcover FLOAT,
    wind_speed FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Market Prices
CREATE TABLE market_prices (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    price_eur_mwh FLOAT,
    price_uah_mwh FLOAT,
    min_price FLOAT,
    max_price FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Optimization History (Feedback Loop)
CREATE TABLE optimization_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    predicted_action INT,
    actual_action INT,
    recommended_cost FLOAT,
    actual_cost FLOAT,
    battery_soc_start FLOAT,
    battery_soc_end FLOAT,
    solar_actual FLOAT,
    load_actual FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RL Agent Training Logs
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
```

---

## Project Structure (V2)

```
smart-energy-ai/
├── src/
│   ├── data_pipeline/
│   │   ├── ingest_weather.py       # Fetch Open-Meteo API
│   │   ├── ingest_prices.py        # Fetch OREE data
│   │   ├── ingest_iot.py           # Fetch/simulate sensor data
│   │   ├── validate.py             # Data quality checks
│   │   └── preprocess.py           # Feature engineering
│   ├── rl_agent/
│   │   ├── env.py                  # Custom gym environment
│   │   ├── train.py                # PPO training loop
│   │   ├── evaluate.py             # Validation & testing
│   │   └── inference.py            # Daily prediction serving
│   ├── optimization/
│   │   ├── optimizer_v2.py         # (Keep for baseline comparison)
│   │   └── rl_optimizer.py         # New RL-based optimizer
│   ├── orchestration/
│   │   └── scheduler.py            # APScheduler / Airflow DAGs
│   └── utils/
│       ├── db.py                   # Database connections
│       ├── config.py               # Config management
│       └── logging.py              # Structured logging
├── models/
│   ├── rl_agent_v1.pkl            # Trained PPO model
│   └── baseline_price_model.joblib # (Keep for comparison)
├── data/
│   ├── raw/                        # API dumps
│   ├── processed/                  # Feature-engineered data
│   ├── training/                   # RL training datasets
│   └── feedback/                   # Historical actions & costs
├── notebooks/
│   ├── 01_eda.ipynb               # Exploratory analysis
│   ├── 02_rl_training.ipynb       # Agent training walkthrough
│   └── 03_backtesting.ipynb       # Historical validation
├── tests/
│   ├── test_pipeline.py           # Data pipeline tests
│   ├── test_rl_env.py             # Environment tests
│   └── test_integration.py        # End-to-end tests
├── docker/
│   ├── Dockerfile                 # Container image
│   └── docker-compose.yml         # Local dev stack
├── config/
│   ├── pipeline.yaml              # Pipeline config
│   ├── rl_agent.yaml              # RL hyperparameters
│   └── scheduling.yaml            # Cron/scheduler config
├── ARCHITECTURE_V2.md             # This file
├── requirements.txt               # Python dependencies
└── README.md                       # Updated with V2 info
```

---

## Implementation Roadmap

### Week 1-2: Data Pipeline
- [ ] Set up PostgreSQL + connection pooling
- [ ] Implement weather ingest (Open-Meteo)
- [ ] Implement price ingest (OREE scraping or API)
- [ ] Build data validation layer
- [ ] Create feedback loop logging

### Week 3: RL Environment & Training
- [ ] Define custom Gym environment
- [ ] Implement reward function
- [ ] Train baseline PPO agent
- [ ] Create evaluation metrics

### Week 4: Orchestration & Integration
- [ ] Set up APScheduler
- [ ] Wire pipeline → RL agent → output
- [ ] Create daily automation flow
- [ ] Build monitoring/alerting

### Week 5: Dashboard & Reporting
- [ ] Update Streamlit with RL results
- [ ] Add backtesting view (historical performance)
- [ ] Create cost comparison (RL vs baseline vs actual)
- [ ] Performance metrics dashboard

### Week 6: Testing & Documentation
- [ ] Unit tests for pipeline
- [ ] Integration tests end-to-end
- [ ] Load testing (can it handle 1 week? 1 month?)
- [ ] Thesis documentation

---

## Success Metrics for Capstone

✅ **Functional:**
- Daily pipeline runs successfully for 7+ days
- RL agent trains daily, improves performance
- Feedback loop captures actual vs predicted

✅ **Performance:**
- RL agent achieves >20% cost savings vs baseline
- Forecast accuracy: MAPE < 15%
- Pipeline latency: < 5 minutes per cycle

✅ **Production-ready:**
- 95%+ data validation success rate
- Graceful error handling (fails safe)
- Docker containerization
- Audit logs for all decisions

---

## Questions for You

1. **Data source priority:** Real APIs first (OREE prices), or stay with simulation?
2. **Timeline:** How many weeks until presentation?
3. **Database:** PostgreSQL local, or prefer to stay CSV-based?
4. **RL complexity:** PPO (solid) vs custom algorithm?
5. **Presentation focus:** Architecture deep-dive, or demo of savings?

Ready to start Week 1?
