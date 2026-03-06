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

## Implementation Roadmap (3-Week University Capstone)

### Week 1: Data Pipeline + PostgreSQL (Days 1-7)

**Days 1-2: Infrastructure**
- [ ] Install PostgreSQL locally
- [ ] Create 5-table schema (weather, prices, history, rl_logs, config)
- [ ] SQLAlchemy ORM + connection pooling
- [ ] Environment variables (DB_URL, API keys)

**Days 3-4: Data Ingestion**
- [ ] `src/data_pipeline/ingest_weather.py` - Open-Meteo API → PostgreSQL
  - Daily 24h forecast at 6:00 AM
  - Validation: NaN check, bounds (0-2000 W/m²)
  - Fallback: Use yesterday's data if API fails
- [ ] `src/data_pipeline/ingest_prices.py` - OREE Ukraine → PostgreSQL
  - Real DAM prices (24 hours ahead)
  - Parse HTML/API endpoint
  - Validation: Price bounds (1-15 EUR/MWh)
  - Fallback: Use historical average if API down

**Days 5-7: Validation & Testing**
- [ ] `src/data_pipeline/validate.py` - Data quality layer
- [ ] Unit tests: `tests/test_pipeline.py`
- [ ] Collect 7 days of real data for Week 2 training
- [ ] Git commit: "Week 1: Data pipeline + PostgreSQL"

**Output:** PostgreSQL with 7+ days of real weather + OREE prices

---

### Week 2: RL Agent + Airflow Orchestration (Days 8-14)

**Days 1-3: RL Environment & Training**
- [ ] `src/rl_agent/env.py` - Custom gym.Env
  - State: [hour, price, solar_forecast, load_actual, battery_soc, ...]
  - Actions: [charge, discharge, sell, buy, idle]
  - Reward: -(actual_cost - baseline_cost)
- [ ] `src/rl_agent/train.py` - PPO training on Week 1 data
  - Stable-Baselines3 PPO
  - Train on 7 days, validate on day 8
  - Save best model to `models/rl_agent_v1.pkl`
- [ ] `src/rl_agent/evaluate.py` - Backtest performance
  - Compare RL vs baseline cost on historical data
  - Print: "RL saves 25% vs baseline"

**Days 4-5: Airflow DAG**
- [ ] Install Airflow locally
- [ ] Create `dags/daily_energy_optimization.py`
  - DAG schedule: Daily at 6:00 AM
  - Task 1: `fetch_weather` (6:00 - 6:05)
  - Task 2: `fetch_prices` (6:05 - 6:10)
  - Task 3: `preprocess_data` (6:10 - 6:15)
  - Task 4: `train_rl_agent` (6:15 - 6:25)
  - Task 5: `generate_action_plan` (6:25 - 6:30)
  - Task 6: `log_results` (continuous)
- [ ] Error handling: Retry failed tasks, alert on failure
- [ ] DAG monitoring in Airflow UI

**Days 6-7: Dashboard Update**
- [ ] Update `streamlit_dashboard/app.py` Streamlit:
  - Tab 1: Current day plan (RL recommendations)
  - Tab 2: Historical performance (RL vs baseline)
  - Tab 3: Cost savings graph (cumulative)
  - Tab 4: Forecast accuracy (MAPE %)
  - Tab 5: RL training loss over time
- [ ] Git commit: "Week 2: RL agent + Airflow automation"

**Output:** Daily automated RL agent generating optimized plans + visible results

---

### Week 3: Testing, Documentation, Presentation (Days 15-21)

**Days 1-2: Integration & Testing**
- [ ] End-to-end test: Full pipeline runs → RL trains → plan generated
- [ ] Test OREE API edge cases (holiday, network down, format change)
- [ ] Performance test: Pipeline completes in < 5 minutes
- [ ] Data quality on real API (check for missing hours, outliers)
- [ ] Error handling: Graceful failure if API down (use cached data)
- [ ] `tests/test_integration.py` - Full pipeline test

**Days 3-4: Documentation**
- [ ] Update `README.md`:
  - Installation steps (PostgreSQL, Python deps)
  - How to run locally
  - How to deploy to AWS free tier
- [ ] Create `DEPLOYMENT.md`:
  - AWS RDS PostgreSQL setup
  - Airflow on EC2 or Lambda
  - Environment variables
- [ ] Performance metrics doc:
  - RL vs baseline cost savings
  - Forecast accuracy (MAPE)
  - Pipeline latency
  - Uptime metrics

**Days 5-7: Presentation + Final Polish**
- [ ] Presentation slides (10-15 slides):
  - Problem statement (energy cost optimization)
  - V1 architecture (static model)
  - V2 architecture (ETL + RL evolution)
  - Data pipeline diagram
  - RL agent visualization
  - Results: Cost savings %, forecast accuracy
  - Demo: Live Streamlit dashboard + Airflow DAG
  - Future work (sensors, distributed RL, multi-site)
- [ ] Record short demo video (2-3 min)
- [ ] Final git cleanup:
  - Remove debug code
  - .gitignore for secrets
  - Commit: "Week 3: Final documentation + presentation"

**Output:** Presentation-ready capstone with real data + RL agent

---

## Technology Stack (Finalized)

**Data:**
- PostgreSQL (local + AWS free tier later)
- SQLAlchemy ORM
- Pydantic (validation)

**Orchestration:**
- Airflow (local + easy to scale)
- Python 3.9+

**ML/RL:**
- Stable-Baselines3 (PPO)
- Gymnasium (gym environment)
- NumPy / Pandas

**APIs:**
- Open-Meteo (free, no auth)
- OREE Ukraine (scraping or API)

**Dashboard:**
- Streamlit (existing, extend with RL results)
- Plotly (charts)

**Testing:**
- Pytest
- Docker (optional, for consistency)

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
