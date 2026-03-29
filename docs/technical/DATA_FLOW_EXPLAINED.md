# Smart Energy AI - Current Data Flow

## Purpose

This document explains the current runtime data flow honestly. It replaces older descriptions that implied:

- real battery BMS telemetry in the live loop
- a trained end-to-end action model serving BUY/SELL/HOLD directly
- automatic MLflow-backed runtime metric ingestion for every prediction

Those claims are not the current runtime truth.

## Active Runtime Flow

### 1. External signals

The system uses real or near-real external signals where available:

- OREE-backed price data and dashboard price APIs
- Open-Meteo weather data in dashboard and Dagster paths
- tenant configuration stored by the application

### 2. Operational battery and control state

The dashboard maintains the operational battery loop using simulator-backed persisted state:

- battery APIs read and write tenant battery state
- control execution writes command effects back into that same state
- command history and control mode fallbacks are derived from persisted tenant records

This is operationally live inside the app, but it is still simulated telemetry rather than plant telemetry.

### 3. Dagster recommendation path

The primary runtime recommendation path is:

1. market and weather assets ingest or refresh external data
2. client state is built from simulator-backed tenant battery state when available, with config fallback
3. price forecast and optimization assets compute a schedule
4. the dashboard reads a schedule-backed recommendation from `/api/dagster/recommendation`

This path is forecast plus optimizer plus normalization, not end-to-end learned action inference.

### 4. Python fallback recommendation path

When the Dagster recommendation is stale or unavailable, the dashboard falls back to `/api/ml/recommendation`:

1. the route builds live context from tenant config, prices, battery state, and weather
2. it invokes `ml_integration_api.py`
3. the Python bridge applies incumbent rule, optimization, renewable, and live-price logic
4. if explicitly configured, learned-policy mode can attempt MLflow-backed serving through `PredictionService`
5. otherwise the bridge falls back to the incumbent runtime path with explicit provenance

### 5. Diagnostics and registry metadata

MLflow is not the primary runtime authority.

- `/api/mlflow/status` reports experiment and registry diagnostics
- `/api/mlflow/log-metrics` captures local runtime diagnostic events
- MLflow metadata may support experiments, registry inventory, and promotion workflows later
- live runtime truth must still come from `serving`, `contract`, and Dagster snapshot metadata

## Data Provenance Summary

### Real external live data

- market prices
- weather inputs
- tenant configuration

### Simulated operational telemetry

- persisted dashboard battery state
- command history and control state in the live tenant loop
- simulator-updated SoC and related battery state

### Fabricated or experimental training scaffolding

- synthetic history rows
- synthetic labels
- mock-serving behavior when no explicit learned-policy model is configured

## What the Dashboard Should Show

The most defensible dashboard story today is:

- current action recommendation and confidence
- provenance and fallback reason
- serving mode and whether learned-policy mode is actually active
- Dagster snapshot freshness and schedule quality
- optional MLflow diagnostics as registry and experiment metadata

The dashboard should not imply that MLflow reachability alone means a live learned policy is serving production actions.
    ├── IF price > avg × 1.25 AND soc > 50% → DISCHARGE
    └── ELSE → HOLD

80/20 Split:
├── Training: 14,016 samples (80%)
│   └── Used to train XGBoost
│
└── Test: 3,504 samples (20%)
    └── Used to evaluate (72.5% accuracy)
```

---

### Stage 4: Model Training
**Where:** `energy_ml/assets/models.py`

```
XGBoost Classifier:
├── Input: 73 features
├── Output: 4 classes (BUY/SELL/HOLD/DISCHARGE)
├── Training data: 14,016 samples
├── Hyperparameters tuned with Optuna (20 trials)
│
├── Performance:
│   ├── Test accuracy: 72.5%
│   ├── Train accuracy: 79.5% (good gap, no overfitting)
│   ├── Precision: 71.8%
│   ├── Recall: 72.2%
│   └── F1 Score: 72.0%
│
└── Backtesting:
    ├── Simulated on 2-year data
    ├── Total profit: ₴1,826.50
    ├── vs Baseline (simple rules): ₴1,200
    ├── Improvement: +52%
    └── Valid for deployment ✅
```

---

### Stage 5: Real-Time Prediction → Dashboard
**Where:** `energy_ml/assets/recommendations.py` + `dashboard/server/api/`

```
Every 5 minutes (auto-refresh):

1. FETCH CURRENT DATA
   ├── Latest OREE price
   ├── Current weather
   ├── Current battery state
   └── Time/date info

2. FEATURE ENGINEERING
   ├── Apply same 73 features as training
   ├── Normalize same way
   └── Create feature vector

3. PREDICT
   ├── Input: [f1, f2, ..., f73]
   ├── Model: XGBoost
   └── Output: [0.05, 0.15, 0.10, 0.70]
              (BUY, SELL, HOLD, DISCHARGE probs)

4. EXTRACT RECOMMENDATION
   ├── Best class: DISCHARGE (0.70)
   ├── Confidence: 70%
   ├── Rationale: "High price (18.50), SOC high (95%)"
   └── Features used: [list of top 5 influencing]

5. SEND TO DASHBOARD API
   └── POST /api/dagster/recommendation
       {
         "action": "DISCHARGE",
         "confidence": 0.70,
         "price": 18.50,
         "battery_soc": 95.0,
         "rationale": "..."
       }

6. DASHBOARD DISPLAYS
   ├── Component: MLPipelineMonitor
   ├── Store: mlPipelineStore
   ├── Shows: Action, confidence, reason
   └── User sees in 2 seconds
```

---

## 📊 Visual Timeline

```
Historical Phase (Offline)
├── 2-year synthetic data generated
├── 73 features engineered
├── 14,016 training samples prepared
├── XGBoost trained (72.5% accuracy)
└── Model versioned in MLflow

                    ↓ (Once, at startup)

Real-Time Phase (Continuous)
├── Every hour: Fetch fresh data (prices, weather)
├── Every 5 min: Generate features
├── Every 5 min: Predict with trained model
├── Every 5 min: Update dashboard
├── Every prediction: Log to MLflow
└── Every week: Retrain if needed

                    ↓ (Cycle repeats)

User Feedback Loop
├── User sees recommendation
├── User executes action
├── System logs actual profit
├── Compares to predicted
├── Updates model accuracy
└── Triggers retraining if drift detected
```

---

## 🔗 How Dashboard Integration Works

```
Dashboard (Nuxt 4)
│
├── User opens http://localhost:3001
│
├── MLPipelineMonitor component mounts
│
├── mlPipelineStore.initialize() called
│
├── Parallel requests to 3 endpoints:
│   ├── GET /api/dagster/recommendation
│   │   ├── Calls Dagster asset
│   │   ├── Gets current prediction
│   │   └── Returns JSON
│   │
│   ├── GET /api/dagster/schedule-24h
│   │   ├── Generates hourly plan
│   │   └── Returns [24 hour forecasts]
│   │
│   └── GET /api/mlflow/status
│       ├── Queries MLflow registry
│       ├── Gets model metrics
│       └── Returns accuracy trend
│
├── All data rendered in Vue components
│
├── Auto-refresh job scheduled (5 min)
│
└── User can:
    ├── See current recommendation
    ├── View 24-hour plan
    ├── Check model accuracy
    ├── View feature importance
    ├── Monitor drift alerts
    └── Execute recommendation
        └── Logs result to /api/mlflow/log-metrics
```

---

## 💡 Real Example

**Hour 14:30 on 2026-02-07:**

```
DATA COLLECTION:
├── OREE API returns: 14.26 ₴/kWh
├── Weather API returns: 8°C, 65% humidity, 2.1 m/s wind
├── Battery BMS returns: 72.6% SOC, 65.5V, 0.2A discharge
└── System time: 14:30 (afternoon, not peak)

FEATURE ENGINEERING (73 features):
├── time: hour=14, day=Thu, is_peak=false, sin(2π×14/24)=0.707
├── weather: temp=8, humidity=65, wind=2.1, clouds=30%, irr=420W/m²
├── generation: solar_power=2.1kW, wind_power=0.8kW, total=2.9kW
├── battery: soc=72.6%, avail_cap=14.5kWh, charge_rate=1.2kW
├── price: current=14.26, lag_1h=14.18, ma_6h=14.32, level=normal
├── interactions: gen/price=0.203, batt/gen=5.0, discharge_profit=1,033₴
└── [67 more features...]

MODEL PREDICTION:
├── Input: [f1=0.707, f2=8, f3=65, ..., f73=5.0]
├── XGBoost processing: "14.26 is low, SOC is high, gen is good"
└── Output probabilities:
    ├── BUY: 0.05 (price is normal, don't buy)
    ├── SELL: 0.15 (could sell, but not peak yet)
    ├── HOLD: 0.23 (steady state option)
    └── DISCHARGE: 0.57 (WINNER - highest probability)

RECOMMENDATION:
├── Action: DISCHARGE (57% confidence)
├── Rationale: "Price is normal (14.26 ₴/kWh), battery is well charged (72.6%), good time to prepare discharge for upcoming peak hours"
├── Factors:
│   ├── #1 battery_soc (0.12 importance)
│   ├── #2 price_current (0.11 importance)
│   ├── #3 hour_of_day (0.08 importance)
│   ├── #4 wind_power (0.06 importance)
│   └── #5 discharge_profit_potential (0.05 importance)
└── Data freshness: Price updated 1 min ago, weather 28 min ago

DASHBOARD DISPLAY:
├── Action badge: "DISCHARGE" (orange)
├── Confidence bar: 57%
├── Current price: 14.26 ₴/kWh
├── Battery SOC: 72.6%
├── Model accuracy: 72.5% (from MLflow)
├── Accuracy trend: [69.5%, 71.0%, 71.8%, 72.5%] (improving)
├── Top features: [list showing battery SOC most important]
└── Next refresh: In 5 minutes

USER ACTION:
├── Clicks "Execute DISCHARGE"
├── System discharges 3.5 kWh (30 min at 7kW)
├── Records: action=DISCHARGE, confidence=0.57, profit=52.81₴
├── POST /api/mlflow/log-metrics
│   └── MLflow records: prediction was accurate, model credit +1
└── Dashboard updates next refresh showing new battery SOC
```

---

## 🎯 Summary

**Data Flow in One Sentence:**
Real prices + weather + battery → 73 features → XGBoost model (trained on 2-year history) → real-time prediction → 2-second display in dashboard → user executes → profit logged → model improves.

**Cycle Time:**
- Historical training: One-time (44 minutes)
- Real-time prediction: Every 5 minutes
- Feature engineering: Same algorithm always
- Dashboard update: Immediate (<2 sec)
- Retraining: Weekly or on-demand

**Data Quality:**
- All sources cached (price 60s, weather 3h, battery 5m)
- Archived to disk for offline processing
- 73 features normalized (z-score)
- 2-year validation history
- Drift detection monitors performance
