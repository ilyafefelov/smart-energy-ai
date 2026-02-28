# Smart Energy AI - Complete Data Flow

## 🔄 End-to-End Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (Layer 1)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌─────────┐
   │  OREE   │          │ Weather  │          │ Battery │
   │ Prices  │          │   API    │          │  BMS    │
   │ Scraper │          │(OpenWeather)        │ Device  │
   └─────────┘          └──────────┘          └─────────┘
        │                     │                     │
        │ Hourly prices       │ Temp, humidity,     │ Current SOC,
        │ (₴/kWh)             │ wind, clouds,       │ power, health
        │                     │ radiation           │
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  CACHING & ARCHIVAL (6-hour cache)     │
        │                                         │
        │  • Save to data/archived/              │
        │  • Timestamp indexed                   │
        │  • Allow offline processing            │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  CALCULATIONS (Derived Data)            │
        │                                         │
        │  • Solar irradiance from position +    │
        │    cloud cover + time of day           │
        │  • Wind power from wind speed curve    │
        │  • Price classification (peak/off-peak)│
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │   Time   │         │ Weather  │         │ Battery  │
   │ Features │         │ Features │         │ Features │
   │    13    │         │    14    │         │    10    │
   └──────────┘         └──────────┘         └──────────┘
        │                     │                     │
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  FEATURE MATRIX (Layer 2)               │
        │                                         │
        │  • 73 Total Features                    │
        │  • Normalized (z-score)                │
        │  • Timestamped                         │
        │  • Includes price + generation + time  │
        │                                         │
        │  Rows: 1 per hour                      │
        │  Columns: 73 features                  │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  HISTORICAL DATA (Layer 3)              │
        │                                         │
        │  • 2-year synthetic dataset             │
        │  • 17,520 hourly records                │
        │  • Training targets (BUY/SELL/etc)     │
        │  • Created from real patterns           │
        └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
   ┌──────────────┐                        ┌──────────────┐
   │  TRAINING    │                        │  VALIDATION  │
   │   Set 80%    │                        │   Set 20%    │
   │  14,016      │                        │   3,504      │
   │  samples     │                        │   samples    │
   └──────────────┘                        └──────────────┘
        │                                           │
        │                                           │
        └───────────────────────┬───────────────────┘
                                │
                                ▼
        ┌─────────────────────────────────────────┐
        │  MODEL TRAINING (Layer 4)               │
        │                                         │
        │  XGBoost Classifier                     │
        │  • 4 Classes: BUY/SELL/HOLD/DISCHARGE │
        │  • Hyperparameter tuning (Optuna)      │
        │  • 5-fold cross-validation             │
        │  • Backtesting on 2-year data          │
        │                                         │
        │  Result: 72.5% Test Accuracy           │
        │  Profit Simulation: ₴1,826 (2 years)   │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  TRAINED MODEL                          │
        │                                         │
        │  • XGBoost binary weights               │
        │  • Feature importance scores            │
        │  • Ready for predictions                │
        │  • Versioned in MLflow registry         │
        └─────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  REAL-TIME INFERENCE (Layer 5)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  CURRENT DATA REFRESH                   │
        │  (Every hour, or on-demand)             │
        │                                         │
        │  • Fetch latest OREE prices             │
        │  • Get current weather                  │
        │  • Read battery state                   │
        │  • Recalculate solar/wind               │
        │  • Apply current feature engineering    │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  PREDICTION                             │
        │                                         │
        │  Input: 73 current features             │
        │  Model: XGBoost (trained)               │
        │  Output: [BUY prob, SELL prob,          │
        │           HOLD prob, DISCHARGE prob]    │
        │                                         │
        │  Result: Best action + confidence       │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  RECOMMENDATION API                     │
        │                                         │
        │  POST /api/dagster/recommendation       │
        │                                         │
        │  Returns:                               │
        │  • Action: BUY/SELL/HOLD/DISCHARGE     │
        │  • Confidence: 0.92 (92%)               │
        │  • Rationale: "Price low, battery..."   │
        │  • Current price: 14.26 ₴/kWh          │
        │  • Current SOC: 72.6%                   │
        │  • Features used: [all 73]              │
        │  • Data lineage: [sources + timestamps] │
        └─────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD INTEGRATION                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
   ┌─────────────────┐                     ┌──────────────────┐
   │ MLPipelineMonitor│                     │  mlPipelineStore │
   │   Component     │                     │     (Pinia)      │
   │                 │                     │                  │
   │ Shows:          │                     │ Manages:         │
   │ • Recommendation│────calls────→       │ • State          │
   │   (Action +     │                     │ • API requests   │
   │    Confidence)  │                     │ • Auto-refresh   │
   │ • Model accuracy│                     │ • Error handling │
   │ • Features      │                     │                  │
   │ • Trend chart   │                     └──────────────────┘
   │ • Drift alert   │
   └─────────────────┘
        ▲
        │
        └────────────────────────────────┐
                                         │
                                         ▼
                        ┌──────────────────────────────────┐
                        │  REAL-TIME DISPLAY              │
                        │                                 │
                        │  User sees on dashboard:        │
                        │  ✓ "BUY now (92% confidence)" │
                        │  ✓ Price: 14.26 ₴/kWh          │
                        │  ✓ Battery: 72.6% SOC          │
                        │  ✓ Why: "Low price, capacity"  │
                        │  ✓ Features: top 5 factors      │
                        │  ✓ Model: 72.5% accurate       │
                        │                                 │
                        │  Updates: Every 5 minutes       │
                        │  Latency: <2 seconds            │
                        └──────────────────────────────────┘
                                         │
                                         ▼
                        ┌──────────────────────────────────┐
                        │  USER EXECUTES RECOMMENDATION  │
                        │                                 │
                        │  Click: "Execute BUY"          │
                        │  System sends:                 │
                        │  • Action: BUY                 │
                        │  • Confidence: 0.92            │
                        │  • Actual profit result         │
                        └──────────────────────────────────┘
                                         │
                                         ▼
                        ┌──────────────────────────────────┐
                        │  METRICS LOGGING                │
                        │                                 │
                        │  POST /api/mlflow/log-metrics  │
                        │  Log:                          │
                        │  • Predicted vs actual profit   │
                        │  • Accuracy of prediction       │
                        │  • System latency               │
                        │  • Model performance update     │
                        │                                 │
                        │  MLflow tracking server:       │
                        │  • Update model metrics         │
                        │  • Track accuracy trend        │
                        │  • Detect drift                │
                        │  • Plan retraining             │
                        └──────────────────────────────────┘
                                         │
                                         ▼
                        ┌──────────────────────────────────┐
                        │  NEXT CYCLE BEGINS             │
                        │                                 │
                        │  Auto-refresh every 5 min:     │
                        │  • New prices from OREE        │
                        │  • New weather data            │
                        │  • New battery state           │
                        │  • Recalculate features        │
                        │  • New prediction              │
                        │  • Updated dashboard           │
                        └──────────────────────────────────┘
```

---

## 🎯 Data Flow Stages Explained

### Stage 1: Data Scraping & Collection
**Where:** `energy_ml/assets/data_sources.py`

```
Real-time data from 3 sources:
├── OREE API
│   └── Hourly energy prices (₴/kWh)
│   └── Cached 60 sec (stable, fresh)
│
├── OpenWeather API
│   ├── Temperature (°C)
│   ├── Humidity (%)
│   ├── Wind speed (m/s)
│   ├── Cloud cover (%)
│   └── Solar radiation (W/m²)
│   └── Cached 3 hours
│
└── Battery BMS (simulated in demo)
    ├── State of charge (%)
    ├── Voltage (V)
    ├── Current (A)
    ├── Temperature (°C)
    └── Health score (0-100)
    └── Cached 5 min
```

**Saving:** All data automatically saved to `data/archived/` with timestamp index for offline use.

---

### Stage 2: Feature Engineering
**Where:** `energy_ml/assets/features.py`

```
Raw Data (5 sources) → 73 Engineered Features

TIME FEATURES (13):
├── hour_of_day (0-23)
├── day_of_week (0-6)
├── month (1-12)
├── is_peak_hour (boolean)
├── sin/cos encoding (cyclical: hour repeats, not linear)
└── day_of_year, is_weekend, season

WEATHER FEATURES (14):
├── temperature (normalized)
├── humidity (%)
├── wind_speed (m/s)
├── cloud_cover (%)
├── solar_radiation (W/m²)
├── weather_category (rainy/cloudy/clear)
├── 3-hour forecast average
├── 24-hour trend
└── pressure, dewpoint

GENERATION FEATURES (9):
├── solar_irradiance (calculated from position + weather)
├── wind_power (from wind speed curve)
├── combined_generation (solar + wind)
├── generation/battery ratio
├── generation/price ratio
└── forecast next hour

BATTERY FEATURES (10):
├── soc_percent (0-100)
├── charge_rate (kW)
├── discharge_rate (kW)
├── available_capacity (kWh)
├── battery_health (0-100)
├── time_to_empty (hours)
├── time_to_full (hours)
├── temperature (°C)
└── charge/discharge efficiency (%)

PRICE FEATURES (14):
├── current_price (₴/kWh)
├── price_lag_1h, lag_2h, lag_6h
├── moving_average_6h, ma_24h
├── price_change (%), volatility
├── price_level (peak/normal/off-peak)
├── forecast_next_hour, next_3h
└── daily_min/max

INTERACTION FEATURES (12):
├── gen/price ratio (generation opportunity)
├── battery/gen ratio (capacity efficiency)
├── price/battery ratio (arbitrage potential)
├── solar_efficiency (irradiance → power)
├── wind_efficiency (wind speed → power)
├── charge_value (capacity × price)
├── discharge_profit (soc × price)
└── composite opportunity score

All normalized using z-score (mean=0, std=1)
All timestamped (YYYY-MM-DD HH:MM:SS)
```

---

### Stage 3: Training Data Preparation
**Where:** `energy_ml/assets/training.py`

```
Historical Data Collection:
├── 2-year synthetic dataset generated from real patterns
├── 17,520 hourly records (365 days × 24 hours × 2 years)
├── Each record has:
│   ├── 73 features (from Stage 2)
│   ├── Target label: BUY/SELL/HOLD/DISCHARGE
│   └── Timestamp
│
└── Target generation logic:
    ├── IF price < avg × 0.85 AND soc < 80% → BUY
    ├── IF price > avg × 1.15 → SELL
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
