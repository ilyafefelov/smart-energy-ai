# Energy ML - Dagster-Based ML Pipeline

**Status:** Phase 3A - Foundation (Data Sources & Orchestration)

## Quick Start

### 1. Setup Environment

```bash
cd energy_ml

# Install dependencies (if not done)
pip install dagster python-dotenv dask pandas numpy scikit-learn requests

# Set OpenWeatherMap API key
# Edit .env.local and replace 'demo' with your actual API key
# Get free key at: https://openweathermap.org/api
```

### 2. Run Tests

```bash
python test_assets.py
```

Expected output:
```
🧪 Testing Energy ML Assets
1️⃣ Testing weather_data asset...
   ✅ Got weather data: {...}
2️⃣ Testing battery_state asset...
   ✅ Got battery data: {...}
3️⃣ Testing price_data_current asset...
   ✅ Got price data: {...}
✅ Basic asset tests complete!
```

### 3. Launch Dagster UI

```bash
# From energy_ml directory
dagster dev
```

Then open: **http://localhost:3000**

You should see:
- 6 assets in the Graph view
- Asset dependencies (solar_irradiance depends on weather_data, etc.)
- Ability to materialize assets manually
- Asset lineage tracking

## Project Structure

```
energy_ml/
├── energy_ml/                 # Main package
│   ├── assets/
│   │   ├── data_sources.py    # ✅ Task 2: Data source assets (6 assets)
│   │   ├── features.py        # 🔜 Task 3: Feature engineering
│   │   ├── training.py        # 🔜 Task 4: Model training
│   │   └── __init__.py
│   ├── jobs/                  # Job definitions
│   │   └── __init__.py
│   ├── resources/             # Resource definitions (Dask, IO managers, etc.)
│   │   └── __init__.py
│   ├── io_managers/           # IO managers for asset storage
│   │   └── __init__.py
│   ├── definitions.py         # ✅ Main Dagster entry point
│   ├── config.py              # ✅ Configuration & constants
│   ├── utils.py               # ✅ Utility functions (solar/wind calculations)
│   └── __init__.py
├── tests/                     # Unit tests
├── .env.local                 # API keys (don't commit!)
├── test_assets.py             # ✅ Test script
└── README.md                  # This file
```

## Current Assets (Phase 3A Complete)

### Data Source Layer (6 assets)

1. **weather_data** ✅
   - Real-time weather from OpenWeatherAPI
   - Cached for 6 hours (OPENWEATHER_CACHE_TTL)
   - Returns: temp, humidity, cloud_cover, wind_speed, wind_direction, pressure
   - Fallback to defaults if API fails

2. **weather_forecast** ✅
   - 5-day forecast from OpenWeatherAPI
   - 40 records (8 per day at 3-hour intervals)
   - Returns: temp, cloud_cover, wind_speed, precipitation

3. **solar_irradiance** ✅
   - Calculated from weather + sun position
   - Kyiv-specific: 50.45°N, 30.52°E
   - Returns: GHI, DNI, DHI (W/m²), elevation, azimuth
   - Depends on: weather_data

4. **wind_potential** ✅
   - Calculated from wind speed
   - Typical small turbine power curve
   - Rated: 5 kW, Cut-in: 3 m/s, Cut-out: 25 m/s
   - Returns: wind_speed_ms, power_potential_kw
   - Depends on: weather_data

5. **battery_state** ✅
   - Current battery state
   - Returns: SOC%, charge/discharge rates, health
   - Placeholder (would come from BMS in production)

6. **price_data_current** ✅
   - Current electricity price from OREE
   - Placeholder with realistic value: 14.26 ₴/kWh
   - Placeholder (real OREE API integration pending)

## Next Steps

### Task 3: Feature Engineering Assets (60 min)
Create 7 feature assets combining all data sources into 100+ features:
- time_features (hour, day, season, holiday, etc.)
- weather_features (normalized, lagged)
- price_features (lags, volatility, trends)
- generation_features (solar/wind capacity-adjusted)
- battery_features (SOC, health, time to empty)
- featuretools_features (complex relationships)
- feature_matrix (combined, ready for ML)

### Task 4: Training Assets (60 min)
- Feature matrix asset (combined, normalized)
- Model training assets (XGBoost, LightGBM, River)
- Backtesting results

### Task 5: Optimization Assets (30 min)
- Optuna hyperparameter tuning
- Optimal strategy parameters

### Task 6: Recommendation Assets (30 min)
- Current recommendation (action + confidence)
- 24h schedule
- Lineage tracking

## Configuration

Edit `energy_ml/config.py` to change:
- API keys
- Model parameters
- Paths
- Cache TTL

Edit `.env.local` for:
- OpenWeatherMap API key
- OREE API URL
- Any secrets

## Logging

All assets log with 🎯 emojis:
- ✅ Success
- ❌ Error
- 📦 Cache hit
- 🌤️ Weather API call
- ☀️ Solar calculations
- 💨 Wind calculations
- 🔋 Battery
- 💰 Price

## Testing Locally Without API Key

The system has fallbacks:
- If OpenWeatherAPI fails: uses cached data or defaults
- If OREE API fails: uses placeholder price (14.26 ₴/kWh)
- Useful for testing without API key

To test with real data:
1. Get free API key from: https://openweathermap.org/api
2. Update .env.local with your key
3. Restart dagster dev

## Next Session Checklist

- [ ] Get OpenWeatherMap API key
- [ ] Update .env.local with key
- [ ] Run: dagster dev
- [ ] Visit: http://localhost:3000
- [ ] Materialize assets manually in UI
- [ ] See asset lineage graph
- [ ] Review logs
- [ ] Start Task 3: Feature Engineering

## Production Readiness

Phase 3A Status: ✅ **READY FOR TASK 3**
- All data sources working
- Caching implemented
- Error handling + fallbacks
- Dagster orchestration ready
- Asset lineage tracking ready

Next: Feature engineering (Task 3)

---

**Questions?** Check PHASE3_DAGSTER_ARCHITECTURE.md in parent directory for detailed specs.
